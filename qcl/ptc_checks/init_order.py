from qcl import typer


def run():
    print("All global value def recs:")
    for global_val_def_rec in typer.definition.all_global_value_recs:
        assert isinstance(global_val_def_rec, typer.definition.ValueRecord)
        print("-", global_val_def_rec.name)
