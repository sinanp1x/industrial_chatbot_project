import os
import sys
from pprint import pprint

def run_tests():
    print("--- Starting Basic QA Tests ---")
    
    # 1. Test Log Parser
    print("\n[1] Testing Log Parser...")
    try:
        from core.log_parser import LogParser
        with open("samples/sample_shift_telemetry.log", "r") as f:
            log_content = f.read()
        
        parser = LogParser()
        result = parser.parse_log(log_content)
        
        if result["counts"]["ERROR"] + result["counts"]["FATAL"] == 2:
            print("✅ Log Parser: Successfully parsed errors and fatals.")
        else:
            print(f"❌ Log Parser: Expected 2 errors/fatals, found {result['counts']['ERROR'] + result['counts']['FATAL']}.")
            
        if "ERR_HYD_OVERPRESS" in result["unique_faults"]:
            print("✅ Log Parser: Successfully extracted fault code ERR_HYD_OVERPRESS.")
        else:
            print(f"❌ Log Parser: Failed to extract ERR_HYD_OVERPRESS. Found: {result['unique_faults']}")
    except Exception as e:
        print(f"❌ Log Parser: Exception occurred: {e}")

    # 2. Test Document Loader and Vector Store
    print("\n[2] Testing Document Loader & Vector Store...")
    try:
        from core.doc_loader import DocumentLoader
        from core.vector_store import LocalVectorStore
        
        # We need a mock uploaded file for DocumentLoader
        # DocumentLoader expects Streamlit's UploadedFile which has .name and .getvalue()
        class MockFile:
            def __init__(self, name, content):
                self.name = name
                self.content = content
            def getvalue(self):
                return self.content.encode('utf-8')
                
        with open("samples/sample_manual_press_line.txt", "r") as f:
            manual_content = f.read()
            
        loader = DocumentLoader()
        chunks = loader.load_and_split([MockFile("sample_manual_press_line.txt", manual_content)])
        
        if len(chunks) > 0:
            print(f"✅ Document Loader: Successfully created {len(chunks)} chunks.")
        else:
             print("❌ Document Loader: Failed to create chunks.")
             
        # Initialize VectorStore
        # use a temporary directory for testing
        test_store = LocalVectorStore(storage_dir="./storage/test_faiss_index")
        test_store.clear()
        test_store.add_documents(chunks)
        
        # Test Search
        results = test_store.search("ERR_HYD_OVERPRESS", k=1)
        if results and "ERR_HYD_OVERPRESS" in results[0].page_content:
             print("✅ Vector Store: Successfully indexed and retrieved relevant chunk.")
        else:
             print("❌ Vector Store: Failed to retrieve relevant chunk.")
             
    except Exception as e:
        print(f"❌ Document Loader & Vector Store: Exception occurred: {e}")

    # 3. Test Agent Graph Compilation
    print("\n[3] Testing Agent Graph Compilation...")
    try:
        from agent.graph import build_industrial_graph
        # Mock dependencies
        class MockVectorStore:
             pass
        class MockLogParser:
             pass
        class MockLLM:
             pass
             
        graph = build_industrial_graph(MockVectorStore(), MockLogParser(), MockLLM())
        print("✅ Agent Graph: Successfully compiled.")
    except Exception as e:
        print(f"❌ Agent Graph: Compilation failed: {e}")
        
    print("\n--- Basic QA Tests Complete ---")

if __name__ == "__main__":
    run_tests()
