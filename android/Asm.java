import java.io.*;
import org.antlr.runtime.*;
import org.antlr.runtime.tree.*;
import org.jf.dexlib2.Opcodes;
import org.jf.dexlib2.writer.builder.DexBuilder;
import org.jf.dexlib2.writer.io.FileDataStore;
import org.jf.smali.*;
public class Asm {
  public static void main(String[] a) throws Exception {
    int api = 24;
    DexBuilder b = new DexBuilder(Opcodes.forApi(api));
    java.util.List<File> fs = new java.util.ArrayList<>();
    walk(new File(a[0]), fs);
    for (File f : fs) {
      smaliFlexLexer lexer = new smaliFlexLexer(new InputStreamReader(new FileInputStream(f), "UTF-8"), api);
      lexer.setSourceFile(f);
      CommonTokenStream ts = new CommonTokenStream((TokenSource) lexer);
      smaliParser p = new smaliParser(ts); p.setVerboseErrors(true); p.setApiLevel(api);
      smaliParser.smali_file_return r = p.smali_file();
      if (p.getNumberOfSyntaxErrors() > 0 || lexer.getNumberOfSyntaxErrors() > 0) { System.err.println("erro de sintaxe em " + f); System.exit(1); }
      CommonTree t = (CommonTree) r.getTree();
      CommonTreeNodeStream ns = new CommonTreeNodeStream(t); ns.setTokenStream(ts);
      smaliTreeWalker w = new smaliTreeWalker(ns); w.setApiLevel(api); w.setVerboseErrors(true); w.setDexBuilder(b);
      w.smali_file();
      if (w.getNumberOfSyntaxErrors() > 0) { System.err.println("erro semântico em " + f); System.exit(1); }
    }
    b.writeTo(new FileDataStore(new File(a[1])));
    System.out.println("ok " + fs.size() + " arquivo(s)");
  }
  static void walk(File d, java.util.List<File> o) { for (File f : d.listFiles()) { if (f.isDirectory()) walk(f, o); else if (f.getName().endsWith(".smali")) o.add(f); } }
}
