"""Diagnostic: does the shipped assembly-tools file register its operators?"""
import bpy

TOOLS = "/workspace/documents/altima2000_v6/altima2000_assembly_tools.py"
ns = {"bpy": bpy, "__name__": "altima2000_assembly_tools"}
src = open(TOOLS).read()
try:
    exec(compile(src, TOOLS, "exec"), ns)
    print("EXEC_OK")
except Exception as e:
    import traceback
    traceback.print_exc()
    print("EXEC_FAIL", repr(e))

try:
    ns["register"]()
    print("REGISTER_OK")
except Exception as e:
    import traceback
    traceback.print_exc()
    print("REGISTER_FAIL", repr(e))

try:
    ops = sorted(dir(bpy.ops.altima))
except Exception as e:
    ops = []
    print("DIR_FAIL", repr(e))
print("OPS", ops)
for want in ("trace_modal", "harness_refresh", "harness_show_all",
             "harness_hide_all", "disassemble", "reassemble", "sequence_all"):
    print("HAS %-18s %s" % (want, want in ops))

# also count registered operator classes
n = 0
for name in dir(bpy.types):
    if name.startswith("ALTIMA_OT_"):
        n += 1
print("ALTIMA_OT_CLASSES", n)
print("OP_TEST_DONE")
