"""
Chat-style GUI for Offline PDF Intelligence.

Provides a conversational interface for querying PDFs with:
- Chat-like message history
- Follow-up action chips
- Query history panel
- Document list and tags
"""

import os
import csv
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
from typing import Optional, List, Dict, Any
import threading

# Try to use customtkinter if available, fall back to tkinter
try:
    import customtkinter as ctk
    USE_CUSTOM_TK = True
except ImportError:
    USE_CUSTOM_TK = False

from .extractor import PDFExtractor
from .indexer import BM25Indexer, TFIDFIndexer
from .retriever import QueryRetriever, detect_question_type
from ..utils.db import DatabaseManager
from ..utils.security import sanitize_input, validate_pdf_path


class ChatApp:
    """
    Chat-style GUI for PDF querying.
    
    Evidence-first interface - all responses show direct excerpts
    from documents with page citations.
    """
    
    def __init__(self, root: Optional[tk.Tk] = None):
        """
        Initialize the chat application.
        
        Args:
            root: Tkinter root window (created if not provided)
        """
        self.root = root or tk.Tk()
        self.root.title("Offline PDF Intelligence")
        self.root.geometry("1200x800")
        
        # State
        self.db = DatabaseManager()
        self.extractor = PDFExtractor()
        self.bm25_indexer = BM25Indexer()
        self.tfidf_indexer = TFIDFIndexer()
        self.retriever: Optional[QueryRetriever] = None
        self.current_pdf_path: Optional[str] = None
        self.all_chunks: List[Dict[str, Any]] = []
        self.query_history: List[Dict[str, Any]] = []
        
        # Question types for dropdown
        self.question_types = [
            "Auto-detect",
            "Find",
            "Define", 
            "Extract",
            "List",
            "Locate",
            "Checklist"
        ]
        
        # Setup UI
        self._setup_styles()
        self._create_layout()
        self._load_query_history()
    
    def _setup_styles(self):
        """Configure UI styles."""
        if USE_CUSTOM_TK:
            ctk.set_appearance_mode("dark")
            ctk.set_default_color_theme("blue")
        
        # Colors for chat bubbles
        self.user_msg_bg = "#007AFF" if not USE_CUSTOM_TK else "#0066cc"
        self.user_msg_fg = "white"
        self.bot_msg_bg = "#E9E9EB" if not USE_CUSTOM_TK else "#3a3a3a"
        self.bot_msg_fg = "black" if not USE_CUSTOM_TK else "white"
    
    def _create_layout(self):
        """Create the main UI layout."""
        # Main container with sidebar
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left sidebar
        self._create_sidebar(main_frame)
        
        # Main chat area
        self._create_chat_area(main_frame)
    
    def _create_sidebar(self, parent):
        """Create the left sidebar with document list and tools."""
        sidebar = tk.Frame(parent, width=250, bg="#f5f5f5")
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        sidebar.pack_propagate(False)
        
        # Load PDF button
        load_btn = tk.Button(
            sidebar, text="📁 Load PDF", 
            command=self._load_pdf,
            bg="#4CAF50", fg="white",
            font=("Arial", 11, "bold"),
            pady=10
        )
        load_btn.pack(fill=tk.X, padx=10, pady=10)
        
        # Clear data button
        clear_btn = tk.Button(
            sidebar, text="🗑️ Clear All Data",
            command=self._clear_all_data,
            bg="#f44336", fg="white",
            font=("Arial", 10)
        )
        clear_btn.pack(fill=tk.X, padx=10, pady=5)
        
        # Separator
        ttk.Separator(sidebar, orient='horizontal').pack(fill=tk.X, padx=10, pady=10)
        
        # Loaded documents section
        doc_label = tk.Label(
            sidebar, text="📄 Loaded Documents",
            font=("Arial", 11, "bold"),
            bg="#f5f5f5"
        )
        doc_label.pack(anchor='w', padx=10)
        
        # Document listbox
        self.doc_listbox = tk.Listbox(
            sidebar, 
            font=("Arial", 10),
            height=10,
            selectmode=tk.SINGLE
        )
        self.doc_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.doc_listbox.bind('<<ListboxSelect>>', self._on_doc_select)
        
        # Separator
        ttk.Separator(sidebar, orient='horizontal').pack(fill=tk.X, padx=10, pady=10)
        
        # Query history section
        history_label = tk.Label(
            sidebar, text="📜 Recent Queries",
            font=("Arial", 11, "bold"),
            bg="#f5f5f5"
        )
        history_label.pack(anchor='w', padx=10)
        
        self.history_listbox = tk.Listbox(
            sidebar,
            font=("Arial", 9),
            height=8,
            selectmode=tk.SINGLE
        )
        self.history_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.history_listbox.bind('<<ListboxSelect>>', self._on_history_select)
        
        # Tags section
        tags_label = tk.Label(
            sidebar, text="🏷️ Tags",
            font=("Arial", 11, "bold"),
            bg="#f5f5f5"
        )
        tags_label.pack(anchor='w', padx=10, pady=(10, 0))
        
        self.tags_frame = tk.Frame(sidebar, bg="#f5f5f5")
        self.tags_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
    
    def _create_chat_area(self, parent):
        """Create the main chat area."""
        chat_frame = tk.Frame(parent)
        chat_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Chat history (scrollable)
        self.chat_history = scrolledtext.ScrolledText(
            chat_frame,
            wrap=tk.WORD,
            font=("Arial", 11),
            bg="#ffffff",
            state='disabled'
        )
        self.chat_history.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Configure text tags for different message types
        self.chat_history.tag_configure("user", justify='right', background=self.user_msg_bg, foreground=self.user_msg_fg)
        self.chat_history.tag_configure("bot", justify='left', background=self.bot_msg_bg, foreground=self.bot_msg_fg)
        self.chat_history.tag_configure("excerpt", justify='left', lmargin1=20, lmargin2=20)
        self.chat_history.tag_configure("citation", justify='left', font=("Arial", 9, "italic"))
        self.chat_history.tag_configure("error", foreground="red")
        
        # Follow-up action chips frame
        self.chips_frame = tk.Frame(chat_frame, bg="#f0f0f0")
        self.chips_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Input area at bottom
        input_frame = tk.Frame(chat_frame)
        input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Question type dropdown
        type_label = tk.Label(input_frame, text="Type:")
        type_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.type_var = tk.StringVar(value="Auto-detect")
        self.type_dropdown = ttk.Combobox(
            input_frame,
            textvariable=self.type_var,
            values=self.question_types,
            width=15,
            state="readonly"
        )
        self.type_dropdown.pack(side=tk.LEFT, padx=(0, 10))
        
        # Text entry
        self.query_entry = tk.Entry(
            input_frame,
            font=("Arial", 12),
            relief=tk.SOLID,
            borderwidth=1
        )
        self.query_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.query_entry.bind("<Return>", lambda e: self._send_query())
        
        # Send button
        send_btn = tk.Button(
            input_frame,
            text="Send ➤",
            command=self._send_query,
            bg="#007AFF",
            fg="white",
            font=("Arial", 11, "bold"),
            padx=20
        )
        send_btn.pack(side=tk.RIGHT)
    
    def _load_pdf(self):
        """Load a PDF file and build index."""
        file_path = filedialog.askopenfilename(
            title="Select PDF",
            filetypes=[("PDF files", "*.pdf")]
        )
        
        if not file_path:
            return
        
        # Validate PDF
        is_valid, error = validate_pdf_path(file_path)
        if not is_valid:
            messagebox.showerror("Invalid PDF", error)
            return
        
        try:
            self._show_status(f"Loading {os.path.basename(file_path)}...")
            
            # Extract chunks
            metadata = self.extractor.get_pdf_metadata(file_path)
            is_scanned = metadata.get('is_scanned', False)
            
            if is_scanned:
                if not self.extractor.is_ocr_available():
                    messagebox.showwarning(
                        "OCR Required",
                        "This PDF appears to be scanned but Tesseract OCR is not available.\n\n"
                        "Install tesseract-ocr on your system to enable OCR."
                    )
                    return
            
            # Extract text chunks
            self.all_chunks = self.extractor.extract_chunks(file_path, force_ocr=is_scanned)
            
            if not self.all_chunks:
                messagebox.showerror("No Text Found", "Could not extract text from this PDF.")
                return
            
            # Build indexes
            self.bm25_indexer.build_index(self.all_chunks)
            self.tfidf_indexer.build_index(self.all_chunks)
            self.retriever = QueryRetriever(self.bm25_indexer)
            
            # Save to database
            pdf_id = self.db.insert_pdf_file(
                file_name=os.path.basename(file_path),
                file_path=file_path,
                file_size=metadata['file_size'],
                page_count=metadata['page_count'],
                is_scanned=is_scanned
            )
            
            # Save chunks to database
            for chunk in self.all_chunks:
                self.db.insert_chunk(
                    pdf_id=pdf_id,
                    chunk_index=chunk['chunk_index'],
                    page_number=chunk['page_number'],
                    text=chunk['text'],
                    section_heading=chunk.get('section_heading')
                )
            
            # Update UI
            self.current_pdf_path = file_path
            self.doc_listbox.insert(tk.END, os.path.basename(file_path))
            
            self._show_status(f"Loaded: {os.path.basename(file_path)} ({len(self.all_chunks)} chunks)")
            self._add_bot_message(
                f"✅ Successfully loaded **{os.path.basename(file_path)}**\n\n"
                f"- Pages: {metadata['page_count']}\n"
                f"- Text chunks: {len(self.all_chunks)}\n"
                f"- Type: {'Scanned (OCR)' if is_scanned else 'Text-based'}\n\n"
                "You can now ask questions about this document."
            )
            
        except Exception as e:
            messagebox.showerror("Error loading PDF", str(e))
            self._show_status("Error loading PDF")
    
    def _send_query(self):
        """Send a query and display results."""
        query = self.query_entry.get().strip()
        if not query:
            return
        
        # Sanitize input
        query = sanitize_input(query, max_length=500)
        
        # Get selected question type
        qtype = self.type_var.get()
        if qtype == "Auto-detect":
            detected_type = detect_question_type(query)
        else:
            detected_type = qtype.lower()
        
        # Display user message
        self._add_user_message(query)
        self.query_entry.delete(0, tk.END)
        
        # Process query in background thread
        self._show_typing_indicator()
        
        def process():
            try:
                if not self.retriever:
                    return {"error": "No document loaded"}
                
                # Handle special query types
                if detected_type == 'define':
                    response = self.retriever.handle_define_query(query)
                else:
                    results = self.retriever.retrieve(query, k=5)
                    response = self.retriever.format_response(query, results)
                
                # Save to history
                self.db.save_query(query, detected_type, response.get('total_results', 0))
                self.query_history.append({
                    'query': query,
                    'type': detected_type,
                    'response': response
                })
                
                return response
                
            except Exception as e:
                return {"error": str(e)}
        
        def on_complete(result):
            self._remove_typing_indicator()
            
            if result.get('error'):
                self._add_bot_message(f"❌ Error: {result['error']}", tag="error")
                return
            
            # Format and display response
            self._format_and_display_response(query, result, detected_type)
            
            # Show follow-up chips
            self._show_follow_up_chips(query, result)
        
        # Run in thread
        thread = threading.Thread(target=lambda: on_complete(process()))
        thread.start()
    
    def _format_and_display_response(self, query: str, response: Dict, qtype: str):
        """Format and display a query response."""
        # Display main message
        self._add_bot_message(response.get('message', ''))
        
        # Display excerpts
        excerpts = response.get('excerpts', [])
        for i, excerpt in enumerate(excerpts[:3], 1):  # Show top 3
            text = excerpt.get('text', '')
            page = excerpt.get('page_number', '?')
            score = excerpt.get('score', 0)
            pdf_path = excerpt.get('pdf_path', '')
            
            # Truncate long excerpts for display
            display_text = text[:300] + '...' if len(text) > 300 else text
            
            # Format excerpt card
            excerpt_card = (
                f"\n{'─' * 50}\n"
                f"📎 Result {i} (Relevance: {score:.2f})\n\n"
                f"\"{display_text}\"\n\n"
                f"📄 Page {page}"
            )
            
            if excerpt.get('section_heading'):
                excerpt_card += f" • {excerpt['section_heading']}"
            
            self.chat_history.insert(tk.END, excerpt_card + "\n", "excerpt")
            
            # Add jump-to-source button (as clickable text)
            self.chat_history.insert(tk.END, f"   → Jump to source\n", "citation")
        
        # Display extracted entities if any
        if qtype == 'when' and response.get('extracted_dates'):
            dates = response['extracted_dates']
            self._add_bot_message(f"📅 **Dates found:** {', '.join(dates[:5])}")
        
        if qtype == 'who' and response.get('extracted_names'):
            names = response['extracted_names']
            self._add_bot_message(f"👤 **Names found:** {', '.join(names[:5])}")
        
        # Show suggestions if no results
        if not excerpts and response.get('suggestions'):
            suggestions = '\n'.join(f"• {s}" for s in response['suggestions'])
            self._add_bot_message(f"💡 **Suggestions:**\n{suggestions}")
        
        # Scroll to bottom
        self.chat_history.see(tk.END)
    
    def _show_follow_up_chips(self, query: str, response: Dict):
        """Show follow-up action chips."""
        # Clear existing chips
        for widget in self.chips_frame.winfo_children():
            widget.destroy()
        
        if not response.get('excerpts'):
            return
        
        # Create chips
        chip_actions = [
            ("Show more results", lambda: self._show_more_results(query)),
            ("Export excerpts", lambda: self._export_excerpts(response)),
        ]
        
        for text, command in chip_actions:
            chip = tk.Button(
                self.chips_frame,
                text=text,
                command=command,
                bg="#e0e0e0",
                relief=tk.RAISED,
                padx=10,
                pady=5,
                cursor="hand2"
            )
            chip.pack(side=tk.LEFT, padx=5, pady=5)
    
    def _show_more_results(self, query: str):
        """Show additional search results."""
        if not self.retriever:
            return
        
        results = self.retriever.retrieve(query, k=10)
        response = self.retriever.format_response(query, results[5:])  # Skip first 5
        self._format_and_display_response(query, response, detect_question_type(query))
    
    def _export_excerpts(self, response: Dict):
        """Export excerpts to CSV."""
        file_path = filedialog.asksaveasfilename(
            title="Export Excerpts",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")]
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Document', 'Page', 'Excerpt', 'Score'])
                
                for excerpt in response.get('excerpts', []):
                    writer.writerow([
                        os.path.basename(excerpt.get('pdf_path', '')),
                        excerpt.get('page_number', ''),
                        excerpt.get('text', ''),
                        excerpt.get('score', '')
                    ])
            
            messagebox.showinfo("Export Complete", f"Exported to:\n{file_path}")
            
        except Exception as e:
            messagebox.showerror("Export Error", str(e))
    
    def _clear_all_data(self):
        """Clear all indexed data."""
        if not messagebox.askyesno(
            "Clear All Data",
            "This will delete all indexed documents, query history, and cached data.\n\nContinue?"
        ):
            return
        
        # Clear database
        self.db.clear_all_data()
        
        # Reset state
        self.all_chunks = []
        self.query_history = []
        self.current_pdf_path = None
        self.bm25_indexer = BM25Indexer()
        self.tfidf_indexer = TFIDFIndexer()
        self.retriever = None
        
        # Clear UI
        self.doc_listbox.delete(0, tk.END)
        self.history_listbox.delete(0, tk.END)
        self.chat_history.config(state='normal')
        self.chat_history.delete(1.0, tk.END)
        self.chat_history.config(state='disabled')
        
        # Clear chips
        for widget in self.chips_frame.winfo_children():
            widget.destroy()
        
        self._show_status("All data cleared")
    
    def _load_query_history(self):
        """Load query history from database."""
        history = self.db.get_query_history(limit=20)
        for item in history:
            self.history_listbox.insert(tk.END, item['query_text'])
    
    def _on_doc_select(self, event):
        """Handle document selection."""
        pass  # Could implement document switching here
    
    def _on_history_select(self, event):
        """Handle history item selection."""
        selection = self.history_listbox.curselection()
        if selection:
            idx = selection[0]
            query = self.history_listbox.get(idx)
            self.query_entry.delete(0, tk.END)
            self.query_entry.insert(0, query)
    
    def _add_user_message(self, text: str):
        """Add a user message to chat history."""
        self.chat_history.config(state='normal')
        self.chat_history.insert(tk.END, f"\n{text}\n", "user")
        self.chat_history.config(state='disabled')
        self.chat_history.see(tk.END)
    
    def _add_bot_message(self, text: str, tag: str = "bot"):
        """Add a bot message to chat history."""
        self.chat_history.config(state='normal')
        self.chat_history.insert(tk.END, f"\n{text}\n", tag)
        self.chat_history.config(state='disabled')
        self.chat_history.see(tk.END)
    
    def _show_typing_indicator(self):
        """Show typing indicator."""
        self.chat_history.config(state='normal')
        self.chat_history.insert(tk.END, "\n⏳ Thinking...\n", "citation")
        self.chat_history.config(state='disabled')
        self.chat_history.see(tk.END)
    
    def _remove_typing_indicator(self):
        """Remove typing indicator."""
        self.chat_history.config(state='normal')
        # Remove last line (typing indicator)
        content = self.chat_history.get(1.0, tk.END)
        lines = content.split('\n')
        if lines and 'Thinking' in lines[-2]:
            lines = lines[:-2]
            self.chat_history.delete(1.0, tk.END)
            self.chat_history.insert(tk.END, '\n'.join(lines))
        self.chat_history.config(state='disabled')
    
    def _show_status(self, message: str):
        """Show status message (could add status bar)."""
        self.root.title(f"Offline PDF Intelligence - {message}")
    
    def run(self):
        """Start the application."""
        self.root.mainloop()


def main():
    """Entry point for the chat application."""
    app = ChatApp()
    app.run()


if __name__ == "__main__":
    main()
