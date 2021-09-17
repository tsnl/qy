from qcl import monomorphizer as mm


def run():
    print(">- BEG of LLVM emitter")

    mono_mod_count = mm.modules.count_all_mono_modules()
    for mono_mod_id in range(mono_mod_count):
        field_count = mm.modules.get_mono_mod_field_count(mono_mod_id)
        registered_lambda_count = mm.modules.count_registered_lambdas(mono_mod_id)

        print(f"- MonoModID: {mono_mod_id} ({field_count} fields) ({registered_lambda_count} lambdas)")

        for registered_lambda_ix in range(registered_lambda_count):
            print("  " f"- lambda {registered_lambda_ix}")
            exp_id = mm.modules.get_registered_lambda_at(mono_mod_id, registered_lambda_ix)
            exp_kind = mm.mast.get_node_kind(exp_id)
            exp_info = mm.mast.get_node_info(exp_id)
            print("  " f"  - target exp: {exp_id} (kind: {exp_kind}) (info: {exp_info})")
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
