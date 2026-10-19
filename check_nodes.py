import server

nodes = server._h_mode_neural_network_nodes('thai')
for k, v in nodes.items():
    preview = repr(v[:80]) if v else "EMPTY / NOT FOUND!"
    print(f"Node [{k}]: len={len(v)} | {preview}")
