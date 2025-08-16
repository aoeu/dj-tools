#!/usr/bin/env python3
"""
MetaFLAC GUI Wrapper
A Tkinter-based GUI for editing FLAC metadata using the metaflac command-line tool.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import tkinter.font as tk_font
import subprocess
import os
import sys
import argparse
import re
from pathlib import Path
from datetime import datetime

class MetaFLACGUI:
    def __init__(self, root, scale_factor=1.0, initial_file=None):
        self.root = root
        self.scale_factor = scale_factor
        self.root.title("MetaFLAC GUI - FLAC Metadata Editor")
        
        # Start maximized - Linux/XFCE compatible
        try:
            self.root.attributes('-zoomed', True)  # For Linux
        except tk.TclError:
            # Fallback: maximize manually
            self.root.geometry(f"{self.root.winfo_screenwidth()}x{self.root.winfo_screenheight()}+0+0")
        
        # Scale the window size (fallback if maximized doesn't work)
        base_width, base_height = 800, 700
        scaled_width = int(base_width * scale_factor)
        scaled_height = int(base_height * scale_factor)
        
        # Configure font scaling
        if scale_factor != 1.0:
            default_font = tk_font.nametofont("TkDefaultFont")
            default_font.configure(size=int(default_font['size'] * scale_factor))
            text_font = tk_font.nametofont("TkTextFont")
            text_font.configure(size=int(text_font['size'] * scale_factor))
        
        # Current file path
        self.current_file = initial_file
        
        # Common FLAC tags - reordered with BPM, GENRE, TITLE, ARTIST, ALBUM at top
        self.common_tags = [
            'BPM', 'GENRE', 'TITLE', 'ARTIST', 'ALBUM', 'DATE', 'TRACKNUMBER',
            'ALBUMARTIST', 'COMPOSER', 'PERFORMER', 'CONDUCTOR', 'COMMENT',
            'DISCNUMBER', 'TOTALTRACKS', 'TOTALDISCS', 'MUSICBRAINZ_TRACKID',
            'MUSICBRAINZ_ALBUMID', 'MUSICBRAINZ_ARTISTID', 'ISRC'
        ]
        
        self.setup_ui()
        
        # Load initial file if provided
        if self.current_file:
            self.file_var.set(self.current_file)
            self.load_tags()
        
    def setup_ui(self):
        # Main frame with scaled padding
        padding = int(10 * self.scale_factor)
        main_frame = ttk.Frame(self.root, padding=str(padding))
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # File selection section
        file_frame = ttk.LabelFrame(main_frame, text="File Selection", padding=str(int(5 * self.scale_factor)))
        file_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, padding))
        file_frame.columnconfigure(1, weight=1)
        
        ttk.Button(file_frame, text="Browse", command=self.browse_file).grid(row=0, column=0, padx=(0, int(5 * self.scale_factor)))
        self.file_var = tk.StringVar()
        self.file_entry = ttk.Entry(file_frame, textvariable=self.file_var, state="readonly")
        self.file_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        # Buttons frame for Load and Save
        buttons_frame = ttk.Frame(file_frame)
        buttons_frame.grid(row=0, column=2, padx=(int(5 * self.scale_factor), 0))
        
        ttk.Button(buttons_frame, text="Load Tags", command=self.load_tags).pack(pady=(0, int(2 * self.scale_factor)))
        ttk.Button(buttons_frame, text="Save Tags", command=self.save_tags).pack()
        
        # Success message label (initially hidden)
        self.success_var = tk.StringVar()
        self.success_label = ttk.Label(file_frame, textvariable=self.success_var, foreground="green")
        self.success_label.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(5, 0))
        
        # Custom tag section - left side (1/3 width)
        custom_frame = ttk.LabelFrame(main_frame, text="Custom Tags", padding=str(int(5 * self.scale_factor)))
        custom_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, padding), padx=(0, int(5 * self.scale_factor)))
        custom_frame.columnconfigure(0, weight=1)
        custom_frame.rowconfigure(0, weight=1)
        
        text_height = int(6 * self.scale_factor) if self.scale_factor > 1.2 else 6
        self.custom_tags_text = scrolledtext.ScrolledText(custom_frame, height=text_height, wrap=tk.WORD)
        
        # Set font size for custom tags text area
        if self.scale_factor != 1.0:
            text_font_size = int(10 * self.scale_factor)
            self.custom_tags_text.configure(font=('TkDefaultFont', text_font_size))
        
        self.custom_tags_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Save Tags and Exit button - centered above Metadata Tags section
        save_exit_frame = ttk.Frame(main_frame)
        save_exit_frame.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(0, int(5 * self.scale_factor)), padx=(int(5 * self.scale_factor), 0))
        save_exit_frame.columnconfigure(0, weight=1)  # Center the button
        
        ttk.Button(save_exit_frame, text="Save Tags and Exit", command=self.save_tags_and_exit).grid(row=0, column=0)
        
        # Tags editing section - right side (2/3 width)
        tags_frame = ttk.LabelFrame(main_frame, text="Metadata Tags", padding=str(int(5 * self.scale_factor)))
        tags_frame.grid(row=2, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, padding), padx=(int(5 * self.scale_factor), 0))
        tags_frame.columnconfigure(1, weight=1)
        
        # Set column weights and sizes: Custom tags = 1/3, Metadata tags = 2/3
        main_frame.rowconfigure(1, weight=0)  # Save Tags and Exit button row
        main_frame.rowconfigure(2, weight=1)  # Main content row
        
        # Calculate screen width for proper proportions
        screen_width = self.root.winfo_screenwidth()
        custom_width = int(screen_width * 0.3)  # 30% for custom tags
        
        main_frame.columnconfigure(0, weight=0, minsize=custom_width)  # Custom tags column (fixed at ~1/3)
        main_frame.columnconfigure(1, weight=1)  # Metadata tags column (takes remaining space)
        
        # Create scrollable frame for tags
        canvas_height = int(300 * self.scale_factor)
        canvas = tk.Canvas(tags_frame, height=canvas_height)
        scrollbar = ttk.Scrollbar(tags_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        tags_frame.rowconfigure(0, weight=1)
        tags_frame.columnconfigure(0, weight=1)
        
        # Store tag entry widgets
        self.tag_entries = {}
        
        # Create entry widgets for common tags with clear buttons
        entry_width = int(40 * self.scale_factor) if self.scale_factor < 1.5 else 40
        
        # Configure columns for proper layout
        scrollable_frame.columnconfigure(0, weight=0, minsize=120)  # Label column - fixed width
        scrollable_frame.columnconfigure(1, weight=1)  # Entry column - expandable
        scrollable_frame.columnconfigure(2, weight=0, minsize=80)  # Button column - fixed width
        
        for i, tag in enumerate(self.common_tags):
            row_padding = int(3 * self.scale_factor)
            col_padding = int(5 * self.scale_factor)
            
            # Tag label
            label = ttk.Label(scrollable_frame, text=f"{tag}:")
            label.grid(row=i, column=0, sticky=tk.W, padx=(0, col_padding), pady=row_padding)
            
            # Entry widget
            entry = ttk.Entry(scrollable_frame, width=entry_width)
            entry.grid(row=i, column=1, sticky=(tk.W, tk.E), pady=row_padding, padx=(0, col_padding))
            self.tag_entries[tag] = entry
            
            # Clear button - using a closure function to properly capture the entry
            def make_clear_command(current_entry):
                return lambda: self.clear_entry(current_entry)
            
            clear_btn = ttk.Button(scrollable_frame, text="delete", 
                                 command=make_clear_command(entry))
            clear_btn.grid(row=i, column=2, pady=row_padding, sticky=tk.W)
        
        # Buttons section - centered Save Tags button
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=3, column=0, columnspan=2, pady=(0, padding))
        buttons_frame.columnconfigure(0, weight=1)  # Allow centering
        
        button_padx = int(5 * self.scale_factor)
        
        # Center the Save Tags button
        center_frame = ttk.Frame(buttons_frame)
        center_frame.grid(row=0, column=0, pady=(0, int(10 * self.scale_factor)))
        
        ttk.Button(center_frame, text="Save Tags", command=self.save_tags).pack()
        
        # Other buttons in a row below, also centered
        other_buttons_frame = ttk.Frame(buttons_frame)
        other_buttons_frame.grid(row=1, column=0)
        
        ttk.Button(other_buttons_frame, text="Remove All Tags", command=self.remove_all_tags).pack(side=tk.LEFT, padx=button_padx)
        ttk.Button(other_buttons_frame, text="Show Raw Output", command=self.show_raw_output).pack(side=tk.LEFT, padx=button_padx)
        ttk.Button(other_buttons_frame, text="Clear Form", command=self.clear_form).pack(side=tk.LEFT, padx=button_padx)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready - Select a FLAC file to begin")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(padding, 0))
        
        # Bind mouse wheel to canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind("<MouseWheel>", _on_mousewheel)
    
    def clear_entry(self, entry_widget):
        """Clear a specific entry widget"""
        entry_widget.delete(0, tk.END)
    
    def check_metaflac(self):
        """Check if metaflac is available"""
        try:
            subprocess.run(['metaflac', '--version'], 
                         capture_output=True, check=True, text=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            messagebox.showerror("Error", 
                               "metaflac command not found. Please install flac package.\n"
                               "On Ubuntu/Debian: sudo apt install flac\n"
                               "On Fedora/RHEL: sudo dnf install flac\n"
                               "On Arch: sudo pacman -S flac")
            return False
    
    def browse_file(self):
        """Browse for FLAC file"""
        filename = filedialog.askopenfilename(
            title="Select FLAC file",
            filetypes=[("FLAC files", "*.flac"), ("All files", "*.*")]
        )
        if filename:
            self.current_file = filename
            self.file_var.set(filename)
            self.status_var.set(f"Selected: {os.path.basename(filename)}")
            # Clear success message when new file is selected
            self.success_var.set("")
    
    def load_tags(self):
        """Load existing tags from FLAC file"""
        if not self.current_file:
            messagebox.showwarning("Warning", "Please select a FLAC file first")
            return
        
        if not self.check_metaflac():
            return
        
        try:
            # Clear existing entries
            self.clear_form()
            
            # Get all tags from the file
            result = subprocess.run(
                ['metaflac', '--export-tags-to=-', self.current_file],
                capture_output=True, text=True, check=True
            )
            
            # Parse the output
            custom_tags = []
            for line in result.stdout.strip().split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.upper()
                    
                    if key in self.tag_entries:
                        self.tag_entries[key].delete(0, tk.END)
                        self.tag_entries[key].insert(0, value)
                    else:
                        custom_tags.append(line)
            
            # Add custom tags to text area
            if custom_tags:
                self.custom_tags_text.delete(1.0, tk.END)
                self.custom_tags_text.insert(1.0, '\n'.join(custom_tags))
            
            self.status_var.set(f"Loaded tags from {os.path.basename(self.current_file)}")
            # Clear success message when loading new tags
            self.success_var.set("")
            
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"Failed to load tags: {e.stderr}")
        except Exception as e:
            messagebox.showerror("Error", f"Unexpected error: {str(e)}")
    
    def save_tags_and_exit(self):
        """Save tags to FLAC file and exit the application"""
        if not self.current_file:
            messagebox.showwarning("Warning", "Please select a FLAC file first")
            return
        
        if not self.check_metaflac():
            return
        
        try:
            # First, remove all existing tags
            subprocess.run(
                ['metaflac', '--remove-all-tags', self.current_file],
                check=True
            )
            
            # Add common tags
            for tag, entry in self.tag_entries.items():
                value = entry.get().strip()
                if value:
                    subprocess.run(
                        ['metaflac', f'--set-tag={tag}={value}', self.current_file],
                        check=True
                    )
            
            # Add custom tags
            custom_text = self.custom_tags_text.get(1.0, tk.END).strip()
            if custom_text:
                for line in custom_text.split('\n'):
                    line = line.strip()
                    if line and '=' in line:
                        subprocess.run(
                            ['metaflac', f'--set-tag={line}', self.current_file],
                            check=True
                        )
            
            # Exit silently after successful save
            self.root.quit()
            
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"Failed to save tags: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Unexpected error: {str(e)}")
    
    def save_tags(self):
        """Save tags to FLAC file"""
        if not self.current_file:
            messagebox.showwarning("Warning", "Please select a FLAC file first")
            return
        
        if not self.check_metaflac():
            return
        
        try:
            # First, remove all existing tags
            subprocess.run(
                ['metaflac', '--remove-all-tags', self.current_file],
                check=True
            )
            
            # Add common tags
            for tag, entry in self.tag_entries.items():
                value = entry.get().strip()
                if value:
                    subprocess.run(
                        ['metaflac', f'--set-tag={tag}={value}', self.current_file],
                        check=True
                    )
            
            # Add custom tags
            custom_text = self.custom_tags_text.get(1.0, tk.END).strip()
            if custom_text:
                for line in custom_text.split('\n'):
                    line = line.strip()
                    if line and '=' in line:
                        subprocess.run(
                            ['metaflac', f'--set-tag={line}', self.current_file],
                            check=True
                        )
            
            # Update status and show success message with datetime
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.status_var.set(f"Tags saved to {os.path.basename(self.current_file)}")
            self.success_var.set(f"{current_time} - Tags saved successfully!")
            
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"Failed to save tags: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Unexpected error: {str(e)}")
    
    def remove_all_tags(self):
        """Remove all tags from FLAC file"""
        if not self.current_file:
            messagebox.showwarning("Warning", "Please select a FLAC file first")
            return
        
        if not messagebox.askyesno("Confirm", "Remove all tags from this file?"):
            return
        
        if not self.check_metaflac():
            return
        
        try:
            subprocess.run(
                ['metaflac', '--remove-all-tags', self.current_file],
                check=True
            )
            self.clear_form()
            self.status_var.set(f"All tags removed from {os.path.basename(self.current_file)}")
            messagebox.showinfo("Success", "All tags removed successfully!")
            
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"Failed to remove tags: {e}")
    
    def show_raw_output(self):
        """Show raw metaflac output in a new window"""
        if not self.current_file:
            messagebox.showwarning("Warning", "Please select a FLAC file first")
            return
        
        if not self.check_metaflac():
            return
        
        try:
            # Get raw output
            result = subprocess.run(
                ['metaflac', '--list', '--block-type=VORBIS_COMMENT', self.current_file],
                capture_output=True, text=True, check=True
            )
            
            # Create new window
            raw_window = tk.Toplevel(self.root)
            raw_window.title(f"Raw MetaFLAC Output - {os.path.basename(self.current_file)}")
            raw_window.geometry("600x400")
            
            text_area = scrolledtext.ScrolledText(raw_window, wrap=tk.WORD)
            text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            text_area.insert(1.0, result.stdout)
            text_area.config(state=tk.DISABLED)
            
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"Failed to get raw output: {e}")
    
    def clear_form(self):
        """Clear all form fields"""
        for entry in self.tag_entries.values():
            entry.delete(0, tk.END)
        self.custom_tags_text.delete(1.0, tk.END)
        # Clear success message when form is cleared
        self.success_var.set("")

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='MetaFLAC GUI - FLAC Metadata Editor')
    parser.add_argument('file', nargs='?', help='FLAC file to load initially')
    parser.add_argument('--scale', type=float, default=1.0, 
                       help='UI scale factor for high-DPI displays (e.g., --scale 2.0)')
    
    args = parser.parse_args()
    
    # Validate file if provided
    initial_file = None
    if args.file:
        if os.path.exists(args.file) and args.file.lower().endswith('.flac'):
            initial_file = os.path.abspath(args.file)
        else:
            print(f"Error: File '{args.file}' does not exist or is not a FLAC file.")
            sys.exit(1)
    
    root = tk.Tk()
    app = MetaFLACGUI(root, scale_factor=args.scale, initial_file=initial_file)
    root.mainloop()

if __name__ == "__main__":
    main()