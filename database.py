import os
from datetime import datetime
import pandas as pd
from pymongo import MongoClient
from pymongo.errors import ConfigurationError, OperationFailure
from bson.objectid import ObjectId
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

class BloodReportDatabase:
    def __init__(self):
        """Initialize MongoDB connection using environment variables or secrets"""
        # Try to get credentials from different sources
        mongodb_uri = st.secrets.get("MONGODB_URI", os.getenv("MONGODB_URI"))
        
        self.client = None
        self.connection_error = None
        
        # Check if connection string is a template/placeholder
        if not mongodb_uri or "<your_username>" in mongodb_uri or "<your_password>" in mongodb_uri:
            self.connection_error = "MongoDB URI not properly configured. Please set up a valid connection string in .env file or Streamlit secrets."
            st.warning(self.connection_error)
            return
            
        try:
            # Connect to MongoDB Atlas
            self.client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
            # Use blood_reports database
            self.db = self.client.blood_reports
            # Check connection with a short timeout
            self.client.admin.command('ping')
            st.success("✅ Connected to MongoDB Atlas successfully!")
        except ConfigurationError as e:
            self.connection_error = f"MongoDB configuration error: {str(e)}"
            st.error(self.connection_error)
        except OperationFailure as e:
            if "Authentication failed" in str(e):
                self.connection_error = "MongoDB authentication failed. Please check your username and password in the connection string."
                st.error(self.connection_error)
                st.info("💡 You need to create your own MongoDB Atlas account and update the connection string.")
            else:
                self.connection_error = f"MongoDB operation failed: {str(e)}"
                st.error(self.connection_error)
        except Exception as e:
            self.connection_error = f"Failed to connect to MongoDB: {str(e)}"
            st.error(self.connection_error)
    
    def save_report(self, user_id, report_data, file_name, report_date=None):
        """Save blood report data for a specific user"""
        if not self.client:
            st.error(self.connection_error or "Database connection not available")
            return None
            
        if report_date is None:
            report_date = datetime.now()
            
        # Convert DataFrame to dict for storage
        if isinstance(report_data, pd.DataFrame):
            report_data_dict = report_data.to_dict('records')
        else:
            report_data_dict = report_data
            
        # Create report document
        report = {
            "user_id": user_id,
            "file_name": file_name,
            "report_date": report_date,
            "created_at": datetime.now(),
            "data": report_data_dict
        }
        
        # Insert into reports collection
        result = self.db.reports.insert_one(report)
        return str(result.inserted_id)
    
    def get_user_reports(self, user_id):
        """Get all reports for a specific user"""
        if not self.client:
            return []
            
        reports = list(self.db.reports.find(
            {"user_id": user_id},
            {"_id": 1, "file_name": 1, "report_date": 1, "created_at": 1}
        ).sort("created_at", -1))
        
        # Convert ObjectId to string for Streamlit
        for report in reports:
            report["_id"] = str(report["_id"])
            
        return reports
    
    def get_report_by_id(self, report_id):
        """Get a specific report by ID"""
        if not self.client or not report_id:
            return None
            
        try:
            report = self.db.reports.find_one({"_id": ObjectId(report_id)})
            if report:
                # Convert ObjectId to string
                report["_id"] = str(report["_id"])
                # Convert data to DataFrame if it exists
                if "data" in report and report["data"]:
                    report["data_df"] = pd.DataFrame(report["data"])
            return report
        except Exception as e:
            print(f"Error fetching report: {str(e)}")
            return None
    
    def delete_report(self, report_id, user_id):
        """Delete a report, ensuring it belongs to the user"""
        if not self.client:
            return False
            
        try:
            result = self.db.reports.delete_one({
                "_id": ObjectId(report_id),
                "user_id": user_id
            })
            return result.deleted_count > 0
        except Exception as e:
            print(f"Error deleting report: {str(e)}")
            return False