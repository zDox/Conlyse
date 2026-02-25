#include "s3_client.hpp"
#include <minio/client.h>
#include <iostream>
#include <fstream>
#include <sstream>

S3Client::S3Client(const S3Config& config) : config_(config) {
    try {
        // Create base URL from endpoint
        minio::s3::BaseUrl base_url(config_.endpoint_url);
        
        // Create static credentials provider
        credentials_provider_ = std::make_unique<minio::creds::StaticProvider>(
            config_.access_key,
            config_.secret_key
        );
        
        // Initialize MinIO client
        minio_client_ = std::make_unique<minio::s3::Client>(
            base_url,
            credentials_provider_.get()
        );
        
        // Log initialization
        std::cout << "[S3Client] Initialized with MinIO SDK:" << std::endl;
        std::cout << "  Endpoint: " << config_.endpoint_url << std::endl;
        std::cout << "  Bucket: " << config_.bucket_name << std::endl;
        std::cout << "  Region: " << config_.region << std::endl;
        
    } catch (const std::exception& e) {
        std::cerr << "[S3Client] Initialization failed: " << e.what() << std::endl;
        throw;
    }
}

S3Client::~S3Client() {
    // MinIO client cleanup handled by unique_ptr
}

bool S3Client::bucket_exists() {
    try {
        minio::s3::BucketExistsArgs args;
        args.bucket = config_.bucket_name;
        
        std::cout << "[S3Client] Checking if bucket exists: " << config_.bucket_name << std::endl;
        
        minio::s3::BucketExistsResponse resp = minio_client_->BucketExists(args);
        
        std::cout << "[S3Client] Bucket exists: " << (resp.exist ? "yes" : "no") << std::endl;
        
        return resp.exist;
        
    } catch (const minio::error::Error& e) {
        std::cerr << "[S3Client] Bucket exists check failed: " << e.what() << std::endl;
        return false;
    } catch (const std::exception& e) {
        std::cerr << "[S3Client] Bucket exists check failed: " << e.what() << std::endl;
        return false;
    }
}

bool S3Client::create_bucket() {
    try {
        minio::s3::MakeBucketArgs args;
        args.bucket = config_.bucket_name;
        
        // Set region if specified
        if (!config_.region.empty()) {
            args.region = config_.region;
        }
        
        std::cout << "[S3Client] Creating bucket: " << config_.bucket_name << std::endl;
        
        minio::s3::MakeBucketResponse resp = minio_client_->MakeBucket(args);
        
        std::cout << "[S3Client] Bucket created successfully" << std::endl;
        
        return true;
        
    } catch (const minio::error::Error& e) {
        std::cerr << "[S3Client] Bucket creation failed: " << e.what() << std::endl;
        
        // Check if bucket already exists (not necessarily an error)
        std::string error_msg = e.what();
        if (error_msg.find("BucketAlreadyOwnedByYou") != std::string::npos ||
            error_msg.find("BucketAlreadyExists") != std::string::npos) {
            std::cout << "[S3Client] Bucket already exists" << std::endl;
            return true;
        }
        
        return false;
    } catch (const std::exception& e) {
        std::cerr << "[S3Client] Bucket creation failed: " << e.what() << std::endl;
        return false;
    }
}

bool S3Client::upload_file(const std::string& local_path, const std::string& s3_key) {
    try {
        // Open file to get size
        std::ifstream file(local_path, std::ios::binary | std::ios::ate);
        if (!file.is_open()) {
            std::cerr << "[S3Client] Failed to open file: " << local_path << std::endl;
            return false;
        }
        
        // Get file size
        std::streamsize file_size = file.tellg();
        file.seekg(0, std::ios::beg);
        
        std::cout << "[S3Client] Uploading file: " << local_path << std::endl;
        std::cout << "[S3Client] File size: " << file_size << " bytes" << std::endl;
        std::cout << "[S3Client] S3 key: " << s3_key << std::endl;
        
        // Create upload arguments
        minio::s3::PutObjectArgs args;
        args.bucket = config_.bucket_name;
        args.object = s3_key;
        args.stream = &file;
        args.object_size = file_size;
        args.content_type = "application/octet-stream";
        
        // Upload file
        minio::s3::PutObjectResponse resp = minio_client_->PutObject(args);
        
        std::cout << "[S3Client] Upload successful" << std::endl;
        std::cout << "[S3Client] ETag: " << resp.etag << std::endl;
        std::cout << "[S3Client] Version ID: " << resp.version_id << std::endl;
        
        return true;
        
    } catch (const minio::error::Error& e) {
        std::cerr << "[S3Client] Upload failed: " << e.what() << std::endl;
        return false;
    } catch (const std::exception& e) {
        std::cerr << "[S3Client] Upload failed: " << e.what() << std::endl;
        return false;
    }
}
