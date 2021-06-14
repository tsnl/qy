# Generated from .\NativeQyModule.g4 by ANTLR 4.9.2
from antlr4 import *
if __name__ is not None and "." in __name__:
    from .NativeQyModuleParser import NativeQyModuleParser
else:
    from NativeQyModuleParser import NativeQyModuleParser

# This class defines a complete generic visitor for a parse tree produced by NativeQyModuleParser.

class NativeQyModuleVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by NativeQyModuleParser#topModule.
    def visitTopModule(self, ctx:NativeQyModuleParser.TopModuleContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#moduleImports.
    def visitModuleImports(self, ctx:NativeQyModuleParser.ModuleImportsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#importLine.
    def visitImportLine(self, ctx:NativeQyModuleParser.ImportLineContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#moduleExports.
    def visitModuleExports(self, ctx:NativeQyModuleParser.ModuleExportsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#exportLine.
    def visitExportLine(self, ctx:NativeQyModuleParser.ExportLineContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#moduleDef.
    def visitModuleDef(self, ctx:NativeQyModuleParser.ModuleDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#typeValIdElement.
    def visitTypeValIdElement(self, ctx:NativeQyModuleParser.TypeValIdElementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#bindValIdElement.
    def visitBindValIdElement(self, ctx:NativeQyModuleParser.BindValIdElementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#bindTypeIdElement.
    def visitBindTypeIdElement(self, ctx:NativeQyModuleParser.BindTypeIdElementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#forceEvalChainElement.
    def visitForceEvalChainElement(self, ctx:NativeQyModuleParser.ForceEvalChainElementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#tableWrapper.
    def visitTableWrapper(self, ctx:NativeQyModuleParser.TableWrapperContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#chainTableWrapper.
    def visitChainTableWrapper(self, ctx:NativeQyModuleParser.ChainTableWrapperContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#moduleAddressPrefix.
    def visitModuleAddressPrefix(self, ctx:NativeQyModuleParser.ModuleAddressPrefixContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#actualTemplateArg.
    def visitActualTemplateArg(self, ctx:NativeQyModuleParser.ActualTemplateArgContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#expr.
    def visitExpr(self, ctx:NativeQyModuleParser.ExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#unitExp.
    def visitUnitExp(self, ctx:NativeQyModuleParser.UnitExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#identityParenExp.
    def visitIdentityParenExp(self, ctx:NativeQyModuleParser.IdentityParenExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#tupleExp.
    def visitTupleExp(self, ctx:NativeQyModuleParser.TupleExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#chainExp.
    def visitChainExp(self, ctx:NativeQyModuleParser.ChainExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#idExp.
    def visitIdExp(self, ctx:NativeQyModuleParser.IdExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#idExpInModule.
    def visitIdExpInModule(self, ctx:NativeQyModuleParser.IdExpInModuleContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#throughIntPrimaryExp.
    def visitThroughIntPrimaryExp(self, ctx:NativeQyModuleParser.ThroughIntPrimaryExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#decFloatExp.
    def visitDecFloatExp(self, ctx:NativeQyModuleParser.DecFloatExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#stringExp.
    def visitStringExp(self, ctx:NativeQyModuleParser.StringExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#throughParenPrimaryExp.
    def visitThroughParenPrimaryExp(self, ctx:NativeQyModuleParser.ThroughParenPrimaryExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#decIntExp.
    def visitDecIntExp(self, ctx:NativeQyModuleParser.DecIntExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#hexIntExp.
    def visitHexIntExp(self, ctx:NativeQyModuleParser.HexIntExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#chainPrimaryExp.
    def visitChainPrimaryExp(self, ctx:NativeQyModuleParser.ChainPrimaryExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#stringPrimaryExp.
    def visitStringPrimaryExp(self, ctx:NativeQyModuleParser.StringPrimaryExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#sqStringChunk.
    def visitSqStringChunk(self, ctx:NativeQyModuleParser.SqStringChunkContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#dqStringChunk.
    def visitDqStringChunk(self, ctx:NativeQyModuleParser.DqStringChunkContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#mlDqStringChunk.
    def visitMlDqStringChunk(self, ctx:NativeQyModuleParser.MlDqStringChunkContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#mlSqStringChunk.
    def visitMlSqStringChunk(self, ctx:NativeQyModuleParser.MlSqStringChunkContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#throughPostfixExp.
    def visitThroughPostfixExp(self, ctx:NativeQyModuleParser.ThroughPostfixExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#getArrayElementExp.
    def visitGetArrayElementExp(self, ctx:NativeQyModuleParser.GetArrayElementExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#dotIntKeyExp.
    def visitDotIntKeyExp(self, ctx:NativeQyModuleParser.DotIntKeyExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#callExp.
    def visitCallExp(self, ctx:NativeQyModuleParser.CallExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#dotNameKeyExp.
    def visitDotNameKeyExp(self, ctx:NativeQyModuleParser.DotNameKeyExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#unaryExp.
    def visitUnaryExp(self, ctx:NativeQyModuleParser.UnaryExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#unaryOp.
    def visitUnaryOp(self, ctx:NativeQyModuleParser.UnaryOpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#binaryExp.
    def visitBinaryExp(self, ctx:NativeQyModuleParser.BinaryExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#powBinaryExp.
    def visitPowBinaryExp(self, ctx:NativeQyModuleParser.PowBinaryExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#mulBinaryExp.
    def visitMulBinaryExp(self, ctx:NativeQyModuleParser.MulBinaryExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#addBinaryExp.
    def visitAddBinaryExp(self, ctx:NativeQyModuleParser.AddBinaryExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#cmpBinaryExp.
    def visitCmpBinaryExp(self, ctx:NativeQyModuleParser.CmpBinaryExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#eqBinaryExp.
    def visitEqBinaryExp(self, ctx:NativeQyModuleParser.EqBinaryExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#logicalAndBinaryExp.
    def visitLogicalAndBinaryExp(self, ctx:NativeQyModuleParser.LogicalAndBinaryExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#logicalOrBinaryExp.
    def visitLogicalOrBinaryExp(self, ctx:NativeQyModuleParser.LogicalOrBinaryExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#assignExp.
    def visitAssignExp(self, ctx:NativeQyModuleParser.AssignExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#bulkyExp.
    def visitBulkyExp(self, ctx:NativeQyModuleParser.BulkyExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#ifExp.
    def visitIfExp(self, ctx:NativeQyModuleParser.IfExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#elseBranchExp.
    def visitElseBranchExp(self, ctx:NativeQyModuleParser.ElseBranchExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#fnExp.
    def visitFnExp(self, ctx:NativeQyModuleParser.FnExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#newExp.
    def visitNewExp(self, ctx:NativeQyModuleParser.NewExpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#newExpAllocatorHint.
    def visitNewExpAllocatorHint(self, ctx:NativeQyModuleParser.NewExpAllocatorHintContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#typeSpec.
    def visitTypeSpec(self, ctx:NativeQyModuleParser.TypeSpecContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#unitTypeSpec.
    def visitUnitTypeSpec(self, ctx:NativeQyModuleParser.UnitTypeSpecContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#identityParenTypeSpec.
    def visitIdentityParenTypeSpec(self, ctx:NativeQyModuleParser.IdentityParenTypeSpecContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#tupleTypeSpec.
    def visitTupleTypeSpec(self, ctx:NativeQyModuleParser.TupleTypeSpecContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#idTypeSpec.
    def visitIdTypeSpec(self, ctx:NativeQyModuleParser.IdTypeSpecContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#idTypeSpecInModule.
    def visitIdTypeSpecInModule(self, ctx:NativeQyModuleParser.IdTypeSpecInModuleContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#throughParenTypeSpec.
    def visitThroughParenTypeSpec(self, ctx:NativeQyModuleParser.ThroughParenTypeSpecContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#throughUnaryTypeSpec.
    def visitThroughUnaryTypeSpec(self, ctx:NativeQyModuleParser.ThroughUnaryTypeSpecContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#structTypeSpec.
    def visitStructTypeSpec(self, ctx:NativeQyModuleParser.StructTypeSpecContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#taggedUnionTypeSpec.
    def visitTaggedUnionTypeSpec(self, ctx:NativeQyModuleParser.TaggedUnionTypeSpecContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#untaggedUnionTypeSpec.
    def visitUntaggedUnionTypeSpec(self, ctx:NativeQyModuleParser.UntaggedUnionTypeSpecContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#arrayTypeSpec.
    def visitArrayTypeSpec(self, ctx:NativeQyModuleParser.ArrayTypeSpecContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#sliceTypeSpec.
    def visitSliceTypeSpec(self, ctx:NativeQyModuleParser.SliceTypeSpecContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#ptrTypeSpec.
    def visitPtrTypeSpec(self, ctx:NativeQyModuleParser.PtrTypeSpecContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#throughBinaryTypeSpec.
    def visitThroughBinaryTypeSpec(self, ctx:NativeQyModuleParser.ThroughBinaryTypeSpecContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#fnSgnTypeSpec.
    def visitFnSgnTypeSpec(self, ctx:NativeQyModuleParser.FnSgnTypeSpecContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by NativeQyModuleParser#effectsSpec.
    def visitEffectsSpec(self, ctx:NativeQyModuleParser.EffectsSpecContext):
        return self.visitChildren(ctx)



del NativeQyModuleParser