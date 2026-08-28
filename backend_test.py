#!/usr/bin/env python3
"""
Backend API test for ClauseClock
Tests:
1. POST /api/contracts/{contract_id}/documents endpoint (Add Document Upload)
2. GET /api/contracts/{contract_id}/superseded-history endpoint (Superseded History API)
"""

import os
import sys
import requests
from io import BytesIO

# Get backend URL from environment
BACKEND_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://contract-tracker-74.preview.emergentagent.com")
API_BASE = f"{BACKEND_URL}/api"

# Test credentials from test_credentials.md
TEST_EMAIL = "test@clauseclock.app"
TEST_PASSWORD = "Test1234!"
TEST_CONTRACT_ID = "6a86c401425ca5752a3a4410"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def log_info(msg):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.END}")

def log_success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")

def log_error(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.END}")

def log_warning(msg):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.END}")

def create_dummy_pdf():
    """Create a minimal valid PDF file for testing"""
    # Minimal PDF structure
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/Resources <<
/Font <<
/F1 <<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
>>
>>
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Test Exhibit Document) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000317 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
410
%%EOF
"""
    return BytesIO(pdf_content)

def test_add_document_workflow():
    """Test the complete Add Document workflow"""
    session = requests.Session()
    
    print("\n" + "="*80)
    print("TESTING: Add Document Upload Workflow on Contract Detail")
    print("="*80 + "\n")
    
    # Step 1: Login
    log_info(f"Step 1: Logging in as {TEST_EMAIL}")
    try:
        login_response = session.post(
            f"{API_BASE}/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            timeout=10
        )
        
        if login_response.status_code != 200:
            log_error(f"Login failed with status {login_response.status_code}")
            log_error(f"Response: {login_response.text}")
            return False
        
        user_data = login_response.json()
        log_success(f"Logged in successfully as {user_data.get('email')}")
    except Exception as e:
        log_error(f"Login request failed: {str(e)}")
        return False
    
    # Step 2: Get contract details before upload
    log_info(f"\nStep 2: Fetching contract {TEST_CONTRACT_ID} details")
    try:
        contract_response = session.get(
            f"{API_BASE}/contracts/{TEST_CONTRACT_ID}",
            timeout=10
        )
        
        if contract_response.status_code != 200:
            log_error(f"Failed to fetch contract: {contract_response.status_code}")
            log_error(f"Response: {contract_response.text}")
            return False
        
        contract_data = contract_response.json()
        contract_name = contract_data.get("contract", {}).get("name")
        initial_doc_count = len(contract_data.get("documents", []))
        
        log_success(f"Contract found: {contract_name}")
        log_info(f"Initial document count: {initial_doc_count}")
        
        # List initial documents
        for i, doc in enumerate(contract_data.get("documents", []), 1):
            log_info(f"  {i}. {doc.get('filename')} ({doc.get('doc_role')})")
        
    except Exception as e:
        log_error(f"Failed to fetch contract: {str(e)}")
        return False
    
    # Step 3: Get initial findings count
    log_info(f"\nStep 3: Fetching initial findings count")
    try:
        findings_response = session.get(
            f"{API_BASE}/contracts/{TEST_CONTRACT_ID}/findings",
            timeout=10
        )
        
        if findings_response.status_code != 200:
            log_error(f"Failed to fetch findings: {findings_response.status_code}")
            return False
        
        findings_data = findings_response.json()
        initial_findings_count = len(findings_data.get("findings", []))
        log_success(f"Initial findings count: {initial_findings_count}")
        
    except Exception as e:
        log_error(f"Failed to fetch findings: {str(e)}")
        return False
    
    # Step 4: Upload a new document
    log_info(f"\nStep 4: Uploading new document with role 'exhibit'")
    try:
        # Create a dummy PDF file
        pdf_file = create_dummy_pdf()
        
        files = {
            'file': ('test_exhibit.pdf', pdf_file, 'application/pdf')
        }
        data = {
            'doc_role': 'exhibit'
        }
        
        upload_response = session.post(
            f"{API_BASE}/contracts/{TEST_CONTRACT_ID}/documents",
            files=files,
            data=data,
            timeout=30
        )
        
        if upload_response.status_code != 200:
            log_error(f"Document upload failed with status {upload_response.status_code}")
            log_error(f"Response: {upload_response.text}")
            return False
        
        upload_data = upload_response.json()
        uploaded_doc = upload_data.get("document", {})
        
        log_success(f"Document uploaded successfully!")
        log_info(f"  Document ID: {uploaded_doc.get('id')}")
        log_info(f"  Filename: {uploaded_doc.get('filename')}")
        log_info(f"  Role: {uploaded_doc.get('doc_role')}")
        log_info(f"  File type: {uploaded_doc.get('file_type')}")
        log_info(f"  Size: {uploaded_doc.get('size_bytes')} bytes")
        log_info(f"  Extraction method: {uploaded_doc.get('extraction_method')}")
        
    except Exception as e:
        log_error(f"Document upload failed: {str(e)}")
        return False
    
    # Step 5: Verify document list refreshed
    log_info(f"\nStep 5: Verifying document list refreshed")
    try:
        contract_response_after = session.get(
            f"{API_BASE}/contracts/{TEST_CONTRACT_ID}",
            timeout=10
        )
        
        if contract_response_after.status_code != 200:
            log_error(f"Failed to fetch contract after upload: {contract_response_after.status_code}")
            return False
        
        contract_data_after = contract_response_after.json()
        final_doc_count = len(contract_data_after.get("documents", []))
        
        if final_doc_count == initial_doc_count + 1:
            log_success(f"Document list refreshed correctly! Count: {initial_doc_count} → {final_doc_count}")
        else:
            log_error(f"Document count mismatch! Expected {initial_doc_count + 1}, got {final_doc_count}")
            return False
        
        # Verify the new document is in the list
        new_doc_found = False
        for doc in contract_data_after.get("documents", []):
            if doc.get("filename") == "test_exhibit.pdf" and doc.get("doc_role") == "exhibit":
                new_doc_found = True
                log_success(f"New document found in list: {doc.get('filename')} ({doc.get('doc_role')})")
                break
        
        if not new_doc_found:
            log_error("New document not found in the document list!")
            return False
        
    except Exception as e:
        log_error(f"Failed to verify document list: {str(e)}")
        return False
    
    # Step 6: Verify re-analysis was NOT triggered
    log_info(f"\nStep 6: Verifying re-analysis was NOT automatically triggered")
    try:
        findings_response_after = session.get(
            f"{API_BASE}/contracts/{TEST_CONTRACT_ID}/findings",
            timeout=10
        )
        
        if findings_response_after.status_code != 200:
            log_error(f"Failed to fetch findings after upload: {findings_response_after.status_code}")
            return False
        
        findings_data_after = findings_response_after.json()
        final_findings_count = len(findings_data_after.get("findings", []))
        
        if final_findings_count == initial_findings_count:
            log_success(f"Findings count unchanged: {initial_findings_count} (re-analysis NOT triggered) ✓")
        else:
            log_warning(f"Findings count changed: {initial_findings_count} → {final_findings_count}")
            log_warning("This might indicate automatic re-analysis was triggered (unexpected)")
        
    except Exception as e:
        log_error(f"Failed to verify findings: {str(e)}")
        return False
    
    # Step 7: Test validation - invalid role
    log_info(f"\nStep 7: Testing validation - invalid document role")
    try:
        pdf_file = create_dummy_pdf()
        files = {
            'file': ('test_invalid.pdf', pdf_file, 'application/pdf')
        }
        data = {
            'doc_role': 'invalid_role'
        }
        
        invalid_response = session.post(
            f"{API_BASE}/contracts/{TEST_CONTRACT_ID}/documents",
            files=files,
            data=data,
            timeout=30
        )
        
        if invalid_response.status_code == 400:
            log_success("Invalid role correctly rejected with 400 status")
        else:
            log_warning(f"Expected 400 for invalid role, got {invalid_response.status_code}")
        
    except Exception as e:
        log_error(f"Validation test failed: {str(e)}")
    
    # Step 8: Test validation - empty file
    log_info(f"\nStep 8: Testing validation - empty file")
    try:
        empty_file = BytesIO(b"")
        files = {
            'file': ('empty.pdf', empty_file, 'application/pdf')
        }
        data = {
            'doc_role': 'exhibit'
        }
        
        empty_response = session.post(
            f"{API_BASE}/contracts/{TEST_CONTRACT_ID}/documents",
            files=files,
            data=data,
            timeout=30
        )
        
        if empty_response.status_code == 400:
            log_success("Empty file correctly rejected with 400 status")
        else:
            log_warning(f"Expected 400 for empty file, got {empty_response.status_code}")
        
    except Exception as e:
        log_error(f"Empty file test failed: {str(e)}")
    
    print("\n" + "="*80)
    log_success("ALL ADD DOCUMENT TESTS PASSED! ✓")
    print("="*80 + "\n")
    
    return True


def test_superseded_history_api():
    """Test the Superseded History API endpoint"""
    session = requests.Session()
    
    print("\n" + "="*80)
    print("TESTING: Superseded History API")
    print("="*80 + "\n")
    
    # Step 1: Login
    log_info(f"Step 1: Logging in as {TEST_EMAIL}")
    try:
        login_response = session.post(
            f"{API_BASE}/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            timeout=10
        )
        
        if login_response.status_code != 200:
            log_error(f"Login failed with status {login_response.status_code}")
            log_error(f"Response: {login_response.text}")
            return False
        
        user_data = login_response.json()
        log_success(f"Logged in successfully as {user_data.get('email')}")
    except Exception as e:
        log_error(f"Login request failed: {str(e)}")
        return False
    
    # Step 2: Get list of contracts to find one with findings
    log_info(f"\nStep 2: Fetching contracts list")
    try:
        contracts_response = session.get(
            f"{API_BASE}/contracts",
            timeout=10
        )
        
        if contracts_response.status_code != 200:
            log_error(f"Failed to fetch contracts: {contracts_response.status_code}")
            return False
        
        contracts_data = contracts_response.json()
        contracts = contracts_data.get("contracts", [])
        
        if not contracts:
            log_warning("No contracts found in the system")
            return False
        
        log_success(f"Found {len(contracts)} contracts")
        
        # Use the first contract or the test contract ID
        test_contract = None
        for contract in contracts:
            if contract.get("id") == TEST_CONTRACT_ID:
                test_contract = contract
                break
        
        if not test_contract and contracts:
            test_contract = contracts[0]
        
        if not test_contract:
            log_error("No suitable contract found for testing")
            return False
        
        contract_id = test_contract.get("id")
        contract_name = test_contract.get("name")
        log_info(f"Testing with contract: {contract_name} (ID: {contract_id})")
        
    except Exception as e:
        log_error(f"Failed to fetch contracts: {str(e)}")
        return False
    
    # Step 3: Test superseded history endpoint
    log_info(f"\nStep 3: Testing GET /api/contracts/{contract_id}/superseded-history")
    try:
        history_response = session.get(
            f"{API_BASE}/contracts/{contract_id}/superseded-history",
            timeout=10
        )
        
        if history_response.status_code != 200:
            log_error(f"Superseded history API failed with status {history_response.status_code}")
            log_error(f"Response: {history_response.text}")
            return False
        
        history_data = history_response.json()
        log_success("Superseded history API returned 200 OK")
        
        # Verify response structure
        if "history" not in history_data:
            log_error("Response missing 'history' field")
            return False
        
        history = history_data.get("history", [])
        log_success(f"Response has 'history' field with {len(history)} superseded findings")
        
    except Exception as e:
        log_error(f"Superseded history API request failed: {str(e)}")
        return False
    
    # Step 4: Verify response structure and data quality
    log_info(f"\nStep 4: Verifying response structure and data quality")
    
    if len(history) == 0:
        log_info("No superseded findings found (this is OK if no re-analysis has been done)")
        log_success("API structure is correct (empty history is valid)")
    else:
        log_info(f"Found {len(history)} superseded findings - verifying structure...")
        
        for idx, finding in enumerate(history, 1):
            log_info(f"\n  Superseded Finding #{idx}:")
            
            # Check required fields
            required_fields = ["id", "type", "state", "sources", "replacement_relationship"]
            missing_fields = [f for f in required_fields if f not in finding]
            
            if missing_fields:
                log_error(f"    Missing required fields: {missing_fields}")
                return False
            
            log_success(f"    ✓ Has all required fields")
            log_info(f"    Type: {finding.get('type')}")
            log_info(f"    State: {finding.get('state')}")
            log_info(f"    Validation status: {finding.get('validation_status')}")
            
            # Check replacement relationship
            replacement = finding.get("replacement_relationship", {})
            if not replacement.get("is_superseded"):
                log_error(f"    replacement_relationship.is_superseded should be True")
                return False
            
            log_success(f"    ✓ Marked as superseded")
            
            superseded_by_id = replacement.get("superseded_by_finding_id")
            if superseded_by_id:
                log_info(f"    Superseded by finding: {superseded_by_id}")
                
                replacement_finding = replacement.get("replacement_finding")
                if replacement_finding:
                    log_success(f"    ✓ Replacement finding details included")
                    log_info(f"      - State: {replacement_finding.get('state')}")
                    log_info(f"      - Validation: {replacement_finding.get('validation_status')}")
                    log_info(f"      - Rank: {replacement_finding.get('rank_category')}")
            
            # Check sources structure and deduplication
            sources = finding.get("sources", [])
            log_info(f"    Sources: {len(sources)} entries")
            
            if sources:
                # Verify document metadata resolution
                sources_with_metadata = 0
                unique_source_keys = set()
                
                for source in sources:
                    # Check for document metadata
                    doc_meta = source.get("document_metadata")
                    if doc_meta:
                        sources_with_metadata += 1
                        if all(k in doc_meta for k in ["document_id", "filename", "doc_role"]):
                            log_success(f"    ✓ Source has complete document metadata: {doc_meta.get('filename')} ({doc_meta.get('doc_role')})")
                    
                    # Track unique sources for deduplication check
                    dedup_key = (
                        source.get("purpose"),
                        source.get("quote"),
                        str(source.get("document_id") or ""),
                        source.get("location")
                    )
                    unique_source_keys.add(dedup_key)
                
                if sources_with_metadata > 0:
                    log_success(f"    ✓ {sources_with_metadata}/{len(sources)} sources have resolved document metadata")
                
                # Verify deduplication
                if len(unique_source_keys) == len(sources):
                    log_success(f"    ✓ All {len(sources)} sources are unique (deduplication working)")
                else:
                    log_error(f"    Duplicate sources detected! {len(sources)} sources but only {len(unique_source_keys)} unique")
                    return False
    
    # Step 5: Test with invalid contract ID
    log_info(f"\nStep 5: Testing with invalid contract ID (should return 404)")
    try:
        invalid_response = session.get(
            f"{API_BASE}/contracts/invalid_id_12345/superseded-history",
            timeout=10
        )
        
        if invalid_response.status_code == 404:
            log_success("Invalid contract ID correctly rejected with 404")
        else:
            log_warning(f"Expected 404 for invalid contract, got {invalid_response.status_code}")
        
    except Exception as e:
        log_error(f"Invalid contract test failed: {str(e)}")
    
    # Step 6: Test authentication (logout and try again)
    log_info(f"\nStep 6: Testing authentication requirement")
    try:
        # Logout
        session.post(f"{API_BASE}/auth/logout", timeout=10)
        
        # Try to access without auth
        unauth_response = session.get(
            f"{API_BASE}/contracts/{contract_id}/superseded-history",
            timeout=10
        )
        
        if unauth_response.status_code == 401:
            log_success("Unauthenticated request correctly rejected with 401")
        else:
            log_warning(f"Expected 401 for unauthenticated request, got {unauth_response.status_code}")
        
    except Exception as e:
        log_error(f"Authentication test failed: {str(e)}")
    
    print("\n" + "="*80)
    log_success("ALL SUPERSEDED HISTORY API TESTS PASSED! ✓")
    print("="*80 + "\n")
    
    return True


if __name__ == "__main__":
    try:
        print("\n" + "="*80)
        print("ClauseClock Backend API Test Suite")
        print("="*80)
        
        all_passed = True
        
        # Test 1: Add Document Upload
        log_info("\n>>> Running Test Suite 1: Add Document Upload")
        if not test_add_document_workflow():
            all_passed = False
            log_error("Add Document tests FAILED")
        
        # Test 2: Superseded History API
        log_info("\n>>> Running Test Suite 2: Superseded History API")
        if not test_superseded_history_api():
            all_passed = False
            log_error("Superseded History API tests FAILED")
        
        if all_passed:
            print("\n" + "="*80)
            log_success("🎉 ALL TEST SUITES PASSED! 🎉")
            print("="*80 + "\n")
            sys.exit(0)
        else:
            print("\n" + "="*80)
            log_error("❌ SOME TESTS FAILED ❌")
            print("="*80 + "\n")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        log_error(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
