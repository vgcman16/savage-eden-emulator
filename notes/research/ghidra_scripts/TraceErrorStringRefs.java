import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Set;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.DataIterator;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Listing;
import ghidra.program.model.symbol.Reference;

public class TraceErrorStringRefs extends GhidraScript {
    private static final String[] TARGETS = new String[] {
        "Unable to read skill information.",
        "error!",
        "Unable to read",
        "skill information"
    };

    @Override
    public void run() throws Exception {
        File outputDir;
        if (getScriptArgs().length > 0) {
            outputDir = new File(getScriptArgs()[0]);
        }
        else {
            outputDir = new File(".");
        }
        outputDir.mkdirs();

        File outputFile = new File(outputDir, currentProgram.getName() + "_error_refs.txt");
        println("Writing analysis to " + outputFile.getAbsolutePath());

        try (PrintWriter out = new PrintWriter(new FileWriter(outputFile))) {
            Map<Function, Set<String>> functionHits = new LinkedHashMap<>();
            writeStringHits(out, functionHits);
            writeFunctionDecompilation(out, functionHits);
        }
    }

    private void writeStringHits(PrintWriter out, Map<Function, Set<String>> functionHits) {
        Listing listing = currentProgram.getListing();
        DataIterator iterator = listing.getDefinedData(true);

        out.println("Program: " + currentProgram.getName());
        out.println("Target string references");
        out.println("========================");

        while (iterator.hasNext() && !monitor.isCancelled()) {
            Data data = iterator.next();
            if (!data.hasStringValue()) {
                continue;
            }

            Object value = data.getValue();
            if (!(value instanceof String)) {
                continue;
            }

            String text = (String) value;
            for (String target : TARGETS) {
                if (!text.contains(target)) {
                    continue;
                }

                out.println();
                out.println("STRING: " + target);
                out.println("  dataAddress: " + data.getAddress());
                out.println("  text: " + text);

                for (Reference ref : getReferencesTo(data.getAddress())) {
                    Function function = getFunctionContaining(ref.getFromAddress());
                    String functionName =
                        function == null ? "<no function>" : function.getName() + " @ " + function.getEntryPoint();
                    out.println("  xref: " + ref.getFromAddress() + " -> " + functionName);
                    if (function != null) {
                        functionHits.computeIfAbsent(function, ignored -> new LinkedHashSet<>()).add(target);
                    }
                }
            }
        }

        out.println();
        out.println("Functions selected for decompilation: " + functionHits.size());
    }

    private void writeFunctionDecompilation(PrintWriter out, Map<Function, Set<String>> functionHits)
            throws Exception {
        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);

        out.println();
        out.println("Decompiled functions");
        out.println("====================");

        for (Map.Entry<Function, Set<String>> entry : functionHits.entrySet()) {
            if (monitor.isCancelled()) {
                break;
            }

            Function function = entry.getKey();
            out.println();
            out.println("FUNCTION: " + function.getName() + " @ " + function.getEntryPoint());
            out.println("TARGETS: " + entry.getValue());
            out.println("----------------------------------------");

            DecompileResults results = decompiler.decompileFunction(function, 60, monitor);
            if (!results.decompileCompleted()) {
                out.println("<decompilation failed>");
                continue;
            }

            out.println(results.getDecompiledFunction().getC());
        }

        decompiler.dispose();
    }
}
