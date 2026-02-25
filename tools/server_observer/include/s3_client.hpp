#ifndef S3_CLIENT_HPP
#define S3_CLIENT_HPP

#include <string>
#include <memory>

// Forward declarations to avoid including MinIO headers in public interface
namespace minio {
    namespace s3 {
        class Client;
    }
    namespace creds {
        class StaticProvider;
    }
}

// Configuration structure (unchanged for backward compatibility)
struct S3Config {
    std::string endpoint_url;
    std::string access_key;
    std::string secret_key;
    std::string bucket_name;
    std::string region;
};

class S3Client {
public:
    S3Client(const S3Config& config);
    ~S3Client();
    
    // Prevent copying
    S3Client(const S3Client&) = delete;
    S3Client& operator=(const S3Client&) = delete;
    
    // Public API (unchanged for backward compatibility)
    bool upload_file(const std::string& local_path, const std::string& s3_key);
    bool bucket_exists();
    bool create_bucket();
    
private:
    S3Config config_;
    std::unique_ptr<minio::s3::Client> minio_client_;
    std::unique_ptr<minio::creds::StaticProvider> credentials_provider_;
};

#endif // S3_CLIENT_HPP
