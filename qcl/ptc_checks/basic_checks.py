"""
This module handles several checks that do not require the VM but that guarantee fitness
to interpret code.

SIDE-EFFECT-SPECIFIERS:
- this is done inductively: just verify the lattice holds.
- in the future, 'try...catch' can be used to lower effects to `Dv` at most.


"""

import functools

from qcl import frontend
from qcl import typer
from qcl import type
from qcl import ast
from qcl import excepts


SES = type.side_effects.SES


def run(project: frontend.Project):
    # TODO: verify side-effects specifiers.
    #   - at each context, there exists a 'highest lattice bound' (HLB)
    #   - in general, any expression (esp. function call, chain, assign expression, throw) can only
    #     use side-effects lower than the HLB.
    #   - exceptions:
    #       - functions may override the HLB in their bodies
    #       - (future) try...catch may execute code with a higher HLB provided errors are caught
    #           - this can be lowered until `Dv`
    
    # TODO: verify that all types are of finite size

    v = Visitor(project)
    v.run()
    
    print("INFO: PTCC: basic_checks OK")


class Visitor(object):
    def __init__(self, project: frontend.Project):
        super().__init__()
        self.project = project
        self.highest_allowed_ses_stack = []

        # initializing the allowed-ses-stack:
        self.push_allowed_ses(SES.Tot)

    def push_allowed_ses(self, allowed_ses: SES):
        self.highest_allowed_ses_stack.append(allowed_ses)

    def pop_allowed_ses(self):
        self.highest_allowed_ses_stack.pop()

    @property
    def top_allowed_ses(self):
        return self.highest_allowed_ses_stack[-1]

    @staticmethod
    def max_ses(*ses_iterator):
        return functools.reduce(Visitor._binary_max_ses, ses_iterator)
        
    @staticmethod
    def _binary_max_ses(ses1, ses2):
        return {
            (SES.Tot, SES.Tot): SES.Tot,
            (SES.Tot, SES.Dv): SES.Dv,
            (SES.Tot, SES.ST): SES.ST,
            (SES.Tot, SES.Exn): SES.Exn,
            (SES.Tot, SES.ML): SES.ML,

            (SES.Dv, SES.Tot): SES.Dv,
            (SES.Dv, SES.Dv): SES.Dv,
            (SES.Dv, SES.ST): SES.ST,
            (SES.Dv, SES.Exn): SES.Exn,
            (SES.Dv, SES.ML): SES.ML,

            (SES.ST, SES.Tot): SES.ST,
            (SES.ST, SES.Dv): SES.ST,
            (SES.ST, SES.ST): SES.ST,
            (SES.ST, SES.Exn): SES.ML,      # notable: push 'up' the lattice
            (SES.ST, SES.ML): SES.ML,

            (SES.Exn, SES.Tot): SES.Exn,
            (SES.Exn, SES.Dv): SES.Exn,
            (SES.Exn, SES.ST): SES.ML,      # notable: push 'up' the lattice
            (SES.Exn, SES.Exn): SES.Exn,
            (SES.Exn, SES.ML): SES.ML,

            (SES.ML, SES.Tot): SES.ML,
            (SES.ML, SES.Dv): SES.ML,
            (SES.ML, SES.ST): SES.ML,
            (SES.ML, SES.Exn): SES.ML,
            (SES.ML, SES.ML): SES.ML 
        }[ses1, ses2]

    def compare_ses(self, compared_ses: SES):
        top_allowed_ses = self.top_allowed_ses
        if top_allowed_ses == SES.Tot:
            return compared_ses == SES.Tot
        elif top_allowed_ses == SES.Dv:
            return compared_ses in (SES.Tot, SES.Dv)
        elif top_allowed_ses == SES.Exn:
            return compared_ses in (SES.Tot, SES.Dv, SES.Exn)
        elif top_allowed_ses == SES.ST:
            return compared_ses in (SES.Tot, SES.Dv, SES.ST)
        elif top_allowed_ses == SES.ML:
            return compared_ses in (SES.Tot, SES.Dv, SES.ST, SES.ML)
        else:
            raise excepts.CompilationError("Unknown side-effects specifier in `compare_ses`")

    def run(self):
        for file_mod_exp in self.project.file_module_exp_list:
            self.check_file_mod_exp(file_mod_exp)

    def check_file_mod_exp(self, file_mod_exp: ast.node.FileModExp):
        for sub_mod_name, sub_mod_exp in file_mod_exp.sub_module_map.items():
            self.check_sub_mod_exp(sub_mod_name, sub_mod_exp)

    def check_sub_mod_exp(self, sub_mod_name: str, sub_mod_exp: ast.node.SubModExp):
        for bind_elem in sub_mod_exp.table.elements:
            self.check_elem(bind_elem)

    def check_elem(self, elem):
        if isinstance(elem, ast.node.BaseBindElem):
            self.check_bind_elem(elem)
        elif isinstance(elem, ast.node.BaseImperativeElem):
            self.check_imp_elem(elem)
        elif isinstance(elem, ast.node.BaseTypingElem):
            # ignore typing elements.
            pass
        else:
            # ignore all other 
            raise NotImplementedError("Unknown Element Type")

    def check_bind_elem(self, bind_elem: ast.node.BaseBindElem):
        if isinstance(bind_elem, ast.node.Bind1VElem):
            self.check_exp(bind_elem.bound_exp)
        elif isinstance(bind_elem, ast.node.Bind1TElem):
            self.check_type_spec(bind_elem.bound_type_spec)
        else:
            raise NotImplementedError("Unknown BindElem instance")

    def check_exp(self, exp: ast.node.BaseExp):
        # TODO: compare each SES using `compare_ses`
        # TODO: extract a SES from expressions
        ses = self.compute_exp_ses(exp)
        if not self.compare_ses(ses):
            msg_suffix = f"Side-effects specifier error: expected <= {self.top_allowed_ses}, got {ses}"
            raise excepts.PtcCheckCompilationError(msg_suffix)

    def check_type_spec(self, ts):
        pass

    def compute_exp_ses(self, exp: ast.node.BaseExp):
        constant_exp_types = (
            ast.node.UnitExp,
            ast.node.StringExp,
            ast.node.NumberExp,
            ast.node.LambdaExp
        )

        if isinstance(exp, constant_exp_types):
            return SES.Tot
        
        elif isinstance(exp, ast.node.IdExp):
            # TODO: perhaps this depends on whether the ID is enclosed or not?
            return SES.Tot
        
        elif isinstance(exp, ast.node.AssignExp):
            dst_ptr_ses = self.compute_exp_ses(exp.dst_exp)
            src_val_ses = self.compute_exp_ses(exp.src_exp)
            return self.max_ses(SES.ST, src_val_ses, dst_ptr_ses)
        elif isinstance(exp, ast.node.IfExp):
            cond_ses = self.compute_exp_ses(exp.cond_exp)
            then_ses = self.compute_exp_ses(exp.then_exp)
            if exp.opt_else_exp:
                else_ses = self.compute_exp_ses(exp.opt_else_exp)
                return self.max_ses(cond_ses, then_ses, else_ses)
            else:
                return self.max_ses(cond_ses, then_ses)
        elif isinstance(exp, ast.node.TupleExp):
            return self.max_ses(*(
                self.compute_exp_ses(item_exp)
                for item_exp in exp.items
            ))
        elif isinstance(exp, ast.node.CastExp):
            # TODO: is this right?
            #   - dynamic casts may cause exceptions
            return self.compute_exp_ses(exp.initializer_data)
        elif isinstance(exp, ast.node.ChainExp):
            ses = exp.opt_prefix_es if exp.opt_prefix_es is not None else SES.Tot
            self.push_allowed_ses(ses)
            for elem in exp.table.elements:
                self.check_elem(elem)
            if exp.opt_tail:
                self.check_exp(exp.opt_tail)
            self.pop_allowed_ses()
            return ses

        elif isinstance(exp, ast.node.PostfixVCallExp):
            called_exp = exp.called_exp
            fn_tid = called_exp.x_tid
            fn_ses = type.side_effects.of(fn_tid)

            if fn_ses != SES.Tot:
                if exp.has_se:
                    msg_suffix = "Function with `Tot` side-effects-specifier called with `!`-call side-effects-specifier"
                    raise excepts.PtcCheckCompilationError(msg_suffix)
            else:
                if not exp.has_se:
                    msg_suffix = "Function with non-`Tot` side-effects-specifier needs `!`-call side-effects-specifier"
                    raise excepts.PtcCheckCompilationError(msg_suffix)

            arg_ses = self.compute_exp_ses(exp.arg_exp)

            return self.max_ses(fn_ses, arg_ses)

        elif isinstance(exp, ast.node.UnaryExp):
            return self.max_ses(
                SES.Tot,
                self.compute_exp_ses(exp.arg_exp)
            )
        elif isinstance(exp, ast.node.BinaryExp):
            return self.max_ses(
                SES.Tot,
                self.compute_exp_ses(exp.lt_arg_exp),
                self.compute_exp_ses(exp.rt_arg_exp)
            )

        else:
            msg = f"TODO: compute SES for {exp.__class__.__name__}"
            raise NotImplementedError(msg)
