@ECHO OFF

SET ANTLR=java -jar .\dev\antlr-4.11.1-complete.jar
SET GFILE=.\grammars\QySourceFile.g4

@ECHO Running ANTLR4...
@%ANTLR% %GFILE% -o .\qcl\parser\antlr\ -no-listener -visitor
@ECHO Done.
