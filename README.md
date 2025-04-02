# Blood Report Analyzer

A powerful tool that extracts, analyzes, and interprets blood test results from PDFs and images, combining traditional OCR with Google's Gemini Vision API for enhanced accuracy.

## Features

- **Multi-Method Extraction**: Uses both specialized pattern-based extraction and Gemini Vision AI to maximize data capture
- **Automatic Result Processing**: Parses and categorizes test results, determining normal/abnormal status
- **Interactive Data Visualization**: View your results in a clean tabular format or an EHR-style interface
- **Comparison View**: Compare different extraction methods to ensure data accuracy
- **Natural Language Q&A**: Ask questions about your results in plain English
- **Smart Filtering**: Removes false positives and ensures only relevant medical data is displayed

## Installation

### Prerequisites

- Python 3.9+
- Pip package manager

### Setup

1. Clone this repository:

   ```bash
   git clone https://github.com/yourusername/blood-report-parser.git
   cd blood-report-parser
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv myenv
   source myenv/bin/activate  # On Windows: myenv\Scripts\activate
   ```

3. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

### Google Gemini API

To use the Gemini Vision feature, you'll need a Google API key:

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey) to get your API key
2. Either:
   - Set it as an environment variable:
     ```bash
     export GEMINI_API_KEY="your-api-key-here"
     ```
   - Or create a .env file in the project root:
     ```
     GEMINI_API_KEY=your-api-key-here
     ```
   - Or enter it directly in the app when prompted

## Usage

1. Start the Streamlit app:

   ```bash
   streamlit run app.py
   ```

2. Access the web interface at http://localhost:8501

3. Upload your blood test report (PDF, JPG, or PNG)

4. The app will automatically process and display your results

5. Use the tabs to:

   - View the combined results
   - Compare extraction methods
   - Analyze Gemini Vision details

6. Ask questions about your results in the Q&A section

## How It Works

### Data Extraction Process

1. **PDF/Image Handling**: Handles various file formats with appropriate preprocessing
2. **Dual Extraction**:
   - **Gemini Vision API**: Uses Google's multimodal model to "see" and understand the report layout
   - **Specialized Medical Extraction**: Uses regex and patterns specific to blood tests
3. **Result Filtering**: Applies medical knowledge to remove false positives and validate real tests
4. **Result Combination**: Merges results from different methods for maximum coverage
5. **Status Determination**: Automatically determines if values are normal, high, or low

### Q&A System

- **Gemini Mode**: Leverages Google's Gemini API for advanced natural language understanding

## Project Structure

```
blood-report-parser/
├── app.py                  # Main Streamlit application
├── blood_parser.py         # Core parser class and extraction logic
├── gemini_vision.py        # Integration with Google's Gemini API
├── medical_extraction.py   # Specialized medical pattern extraction
├── requirements.txt        # Project dependencies
└── README.md               # This file
```

## Technologies Used

- **Streamlit**: Web application framework
- **Pandas**: Data manipulation and analysis
- **Google Gemini API**: Advanced AI for visual document understanding
- **PIL/Pillow**: Image processing
- **PyPDF2/pdf2image**: PDF handling
- **Pytesseract**: OCR for text extraction
- **Regular Expressions**: Pattern matching for specialized extraction

## Limitations

- OCR accuracy depends on the quality of the uploaded document
- API key is required for the Gemini Vision features
- Currently only supports English language reports

## Future Improvements

- Support for multiple languages
- Time-series tracking of values across reports
- Export functionality (PDF, CSV)
- Medical reference information for test results
- Enhanced visualization options

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- Google Gemini API for providing powerful multimodal AI capabilities
- The Streamlit team for their excellent web app framework
- Open-source OCR and document processing libraries

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
