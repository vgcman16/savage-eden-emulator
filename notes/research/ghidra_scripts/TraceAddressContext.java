import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.listing.Listing;
import ghidra.program.model.symbol.Reference;

public class TraceAddressContext extends GhidraScript {
    @Override
    public void run() throws Exception {
        if (getScriptArgs().length < 2) {
            throw new IllegalArgumentException("Usage: TraceAddressContext <hex-address> <output-dir>");
        }

        String addressText = getScriptArgs()[0];
        File outputDir = new File(getScriptArgs()[1]);
        outputDir.mkdirs();

        Address address = toAddr(addressText);
        Function function = getFunctionContaining(address);
        if (function == null) {
            throw new IllegalStateException("No function contains address " + address);
        }

        File outputFile =
            new File(outputDir, currentProgram.getName() + "_" + addressText.replace("0x", "") + "_context.txt");
        println("Writing analysis to " + outputFile.getAbsolutePath());

        try (PrintWriter out = new PrintWriter(new FileWriter(outputFile))) {
            out.println("Program: " + currentProgram.getName());
            out.println("Target address: " + address);
            out.println("Function: " + function.getName() + " @ " + function.getEntryPoint());
            out.println();

            out.println("References to target");
            out.println("====================");
            for (Reference ref : getReferencesTo(address)) {
                Function refFunction = getFunctionContaining(ref.getFromAddress());
                String functionName =
                    refFunction == null ? "<no function>" : refFunction.getName() + " @ " + refFunction.getEntryPoint();
                out.println(ref.getFromAddress() + " -> " + functionName);
            }

            out.println();
            out.println("Instructions around target");
            out.println("=========================");
            writeInstructionWindow(out, address, 16);

            out.println();
            out.println("Function decompilation");
            out.println("======================");
            writeDecompilation(out, function);
        }
    }

    private void writeInstructionWindow(PrintWriter out, Address address, int radius) {
        Listing listing = currentProgram.getListing();
        Instruction start = listing.getInstructionContaining(address);
        if (start == null) {
            out.println("<no instruction at target>");
            return;
        }

        Address windowStart = start.getAddress();
        for (int i = 0; i < radius; i++) {
            Instruction previous = listing.getInstructionBefore(windowStart);
            if (previous == null) {
                break;
            }
            windowStart = previous.getAddress();
        }

        InstructionIterator iterator = listing.getInstructions(windowStart, true);
        int remaining = (radius * 2) + 1;
        while (iterator.hasNext() && remaining > 0) {
            Instruction instruction = iterator.next();
            String marker = instruction.getAddress().equals(start.getAddress()) ? ">>" : "  ";
            out.println(marker + " " + instruction.getAddress() + "  " + instruction);
            remaining--;
        }
    }

    private void writeDecompilation(PrintWriter out, Function function) throws Exception {
        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        try {
            DecompileResults results = decompiler.decompileFunction(function, 60, monitor);
            if (!results.decompileCompleted()) {
                out.println("<decompilation failed>");
                return;
            }
            out.println(results.getDecompiledFunction().getC());
        }
        finally {
            decompiler.dispose();
        }
    }
}
