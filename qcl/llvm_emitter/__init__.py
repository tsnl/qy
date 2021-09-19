from qcl import monomorphizer as mm


def run():
    print(">- BEG of LLVM emitter -<")

    # FIXME: need some way to get substitution used to instantiate PolyMod into MonoMod
    #   - can obtain this from ArgList, translating mtype.TID to type.TID
    #   - can then generate a substitution and an AST node reference (for LambdaExp)
    #   - applying sub to existing type yields subbed type, true for any type in MonoModID

    mono_mod_count = mm.modules.count_all_mono_modules()
    for mono_mod_id in range(mono_mod_count):
        field_count = mm.modules.get_mono_mod_field_count(mono_mod_id)
        registered_lambda_count = mm.modules.count_registered_lambdas(mono_mod_id)

        print(f"- MonoModID: {mono_mod_id} ({field_count} fields) ({registered_lambda_count} lambdas)")
        print(f"  " f"- module source node: {repr(mm.modules.get_source_sub_mod_exp(mono_mod_id))}")

        for registered_lambda_ix in range(registered_lambda_count):
            print("  " f"- lambda {registered_lambda_ix}")
            exp_id = mm.modules.get_registered_lambda_at(mono_mod_id, registered_lambda_ix)
            exp_kind = mm.mast.get_node_kind(exp_id)
            exp_info = mm.mast.get_node_info(exp_id)
            ast_exp = mm.mast.get_ast_node(exp_id)
            print("  " f"  - target exp: {exp_id} (kind: {exp_kind}) (info: {exp_info})")
            print("  " f"    source exp: {ast_exp}")
            assert exp_kind == mm.mast.NodeKind.EXP_Lambda

        for field_ix in range(field_count):
            field_gdef_id = mm.modules.get_mono_mod_field_gdef_id_at(mono_mod_id, field_ix)
            def_kind = mm.gdef.get_def_kind(field_gdef_id)
            def_target = mm.gdef.get_def_target(field_gdef_id)
            
            print("  " f"- field {field_ix}: {def_kind} with target {def_target}")

            if def_kind == mm.gdef.DefKind.ConstTotTID:
                print("  " "  - IGNORED")    
            elif def_kind == mm.gdef.DefKind.ConstTotVal:
                print("  " "  - TODO: emit me!")
            else:
                print("  " "  - ERROR: how did this DefKind get here?")

    # PLAN:
    #   - first, declare all types
    #   - then, define all types
    #   - next, declare all synthetic functions (one per lambda)
    #       - requires info about implicit arguments
    #   - next, declare global variables
    #   - next, process function definitions & global variable initializers

    print(">- END of LLVM emitter -<")