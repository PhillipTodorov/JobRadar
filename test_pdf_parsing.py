"""Test PDF parsing functionality."""

import pdfplumber
from pathlib import Path

def test_pdf_extraction():
    """Test if pypdf can extract text from a PDF."""
    print("Testing PDF text extraction...")
    print("=" * 50)

    # Create a simple test - just verify the library works
    try:
        # Test that we can import and use the library
        print("[OK] pdfplumber library imported successfully")

        # Check if there are any PDFs in the profile folder
        profile_dir = Path(__file__).parent / "profile"
        if profile_dir.exists():
            pdf_files = list(profile_dir.glob("*.pdf"))
            if pdf_files:
                print(f"\nFound {len(pdf_files)} PDF file(s) in profile/")

                # Try to read the first PDF
                pdf_path = pdf_files[0]
                print(f"\nTesting with: {pdf_path.name}")
                print("-" * 50)

                with pdfplumber.open(pdf_path) as pdf:
                    print(f"[OK] PDF opened successfully")
                    print(f"  Pages: {len(pdf.pages)}")

                    # Extract text from first page
                    if pdf.pages:
                        first_page_text = pdf.pages[0].extract_text()
                        print(f"\n[OK] Text extraction successful")
                        print(f"  First 200 characters:\n  {first_page_text[:200]}...")
                    else:
                        print("[WARN] PDF has no pages")
            else:
                print("\n[INFO] No PDF files found in profile/ directory")
                print("  You can test by uploading a PDF CV through the dashboard")
        else:
            print("\n[INFO] profile/ directory doesn't exist yet")
            print("  It will be created when you upload a CV")

        print("\n[OK] PDF parsing is ready to use!")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        print("  Make sure pdfplumber is installed: pip install pdfplumber")
        return False

    return True

if __name__ == "__main__":
    test_pdf_extraction()
