@ECHO OFF

SET ANTLR=java -jar .\dev\antlr-4.9.2-complete.jar
SET GFILE=.\grammars\QySourceFile.g4

@ECHO Running ANTLR4...
@%ANTLR% %GFILE% -o .\qcl\antlr\ -no-listener -visitor
@ECHO Done.
