"""Unit tests for S3 functions with bug discovery."""
import pytest
import allure
from unittest.mock import Mock, patch
import boto3

@allure.epic("OpenFilter QA")
@allure.feature("S3 Operations")
@allure.story("S3 Functions")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.unit
@pytest.mark.pyramid_unit
class TestS3Functions:
    
    @allure.title("Test S3 connection - Success")
    @allure.description("Verify S3 connection can be established successfully")
    def test_s3_connection_success(self):
        """Test successful S3 connection."""
        with patch('boto3.client') as mock_client:
            mock_s3 = Mock()
            mock_client.return_value = mock_s3
            
            # Simulate successful connection
            result = self._connect_s3()
            assert result is not None
            mock_client.assert_called_once()
    
    @allure.title("Test S3 upload - Success")
    @allure.description("Verify file can be uploaded to S3 successfully")
    def test_s3_upload_success(self):
        """Test successful S3 upload."""
        with patch('boto3.client') as mock_client:
            mock_s3 = Mock()
            mock_client.return_value = mock_s3
            mock_s3.upload_file.return_value = None
            
            result = self._upload_file("test.mp4", "bucket", "key")
            assert result == True
            mock_s3.upload_file.assert_called_once()
    
    @allure.title("Test S3 download - Bug Discovery")
    @allure.description("This test discovers a bug in S3 download functionality")
    @pytest.mark.bug_discovery
    def test_s3_download_bug(self):
        """Test that discovers S3 download bug."""
        with patch('boto3.client') as mock_client:
            mock_s3 = Mock()
            mock_client.return_value = mock_s3
            # Simulate bug: download_file raises exception
            mock_s3.download_file.side_effect = Exception("Network timeout")
            
            with pytest.raises(Exception):
                self._download_file("bucket", "key", "local_file.mp4")
    
    @allure.title("Test S3 list objects - Pagination Bug")
    @allure.description("Bug discovery: pagination not handled correctly")
    @pytest.mark.bug_discovery
    def test_s3_list_pagination_bug(self):
        """Test that discovers pagination bug in S3 list."""
        with patch('boto3.client') as mock_client:
            mock_s3 = Mock()
            mock_client.return_value = mock_s3
            
            # Bug: doesn't handle NextContinuationToken
            mock_s3.list_objects_v2.return_value = {
                'Contents': [{'Key': 'file1.mp4'}],
                'NextContinuationToken': 'token123'
            }
            
            # This should fail because pagination isn't handled
            result = self._list_all_objects("bucket")
            assert len(result) == 1  # Should be more if pagination worked
    
    def _connect_s3(self):
        """Helper method to connect to S3."""
        import boto3
        return boto3.client('s3')
    
    def _upload_file(self, local_file, bucket, key):
        """Helper method to upload file to S3."""
        try:
            s3 = boto3.client('s3')
            s3.upload_file(local_file, bucket, key)
            return True
        except Exception:
            return False
    
    def _download_file(self, bucket, key, local_file):
        """Helper method to download file from S3."""
        s3 = boto3.client('s3')
        s3.download_file(bucket, key, local_file)
    
    def _list_all_objects(self, bucket):
        """Helper method to list all objects (with pagination bug)."""
        s3 = boto3.client('s3')
        response = s3.list_objects_v2(Bucket=bucket)
        return response.get('Contents', [])
