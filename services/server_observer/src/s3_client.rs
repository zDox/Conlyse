use minio::s3::builders::ObjectContent;
use minio::s3::client::ClientBuilder;
use minio::s3::creds::StaticProvider;
use minio::s3::error::{Error as MinioError, ErrorCode};
use minio::s3::http::BaseUrl;
use minio::s3::types::S3Api;
use minio::s3::Client;
use serde::Deserialize;
use std::path::Path;
use thiserror::Error;

#[derive(Debug, Clone, Deserialize)]
pub struct S3Config {
    pub endpoint_url: String,
    pub access_key: String,
    pub secret_key: String,
    pub bucket_name: String,
    pub region: String,
}

#[derive(Clone)]
pub struct S3Client {
    cfg: S3Config,
    client: Client,
}

impl S3Client {
    pub async fn new(cfg: S3Config) -> Result<Self, S3Error> {
        let base_url = cfg
            .endpoint_url
            .parse::<BaseUrl>()
            .map_err(|err| S3Error::Sdk(err.to_string()))?;
        let provider = StaticProvider::new(&cfg.access_key, &cfg.secret_key, None);
        let client = ClientBuilder::new(base_url)
            .provider(Some(Box::new(provider)))
            .build()
            .map_err(|err| S3Error::Sdk(err.to_string()))?;

        let s3 = Self { cfg, client };

        // Match C++ behavior: verify bucket and create it if missing.
        s3.ensure_bucket_exists().await?;
        Ok(s3)
    }

    async fn ensure_bucket_exists(&self) -> Result<(), S3Error> {
        if self.bucket_exists().await? {
            return Ok(());
        }

        self.create_bucket().await
    }

    pub async fn bucket_exists(&self) -> Result<bool, S3Error> {
        let resp = self
            .client
            .bucket_exists(&self.cfg.bucket_name)
            .send()
            .await
            .map_err(|err| S3Error::Sdk(err.to_string()))?;
        Ok(resp.exists)
    }

    pub async fn create_bucket(&self) -> Result<(), S3Error> {
        let create_req = self
            .client
            .create_bucket(&self.cfg.bucket_name)
            .region((!self.cfg.region.is_empty()).then_some(self.cfg.region.clone()));
        match create_req.send().await {
            Ok(_) => Ok(()),
            Err(err) if is_bucket_already_exists_error(&err) => Ok(()),
            Err(err) => Err(S3Error::Sdk(err.to_string())),
        }
    }

    pub async fn upload_file<P: AsRef<Path>>(
        &self,
        local_path: P,
        s3_key: &str,
    ) -> Result<(), S3Error> {
        let path = local_path.as_ref();
        self.client
            .put_object_content(&self.cfg.bucket_name, s3_key, ObjectContent::from(path))
            .send()
            .await
            .map_err(|err| S3Error::Sdk(err.to_string()))?;

        Ok(())
    }

    /// Upload object content directly from an in-memory buffer without
    /// touching the local filesystem. This is useful when the caller
    /// already has compressed bytes and does not want to persist a
    /// temporary file on disk.
    pub async fn upload_bytes(
        &self,
        data: Vec<u8>,
        s3_key: &str,
    ) -> Result<(), S3Error> {
        self.client
            .put_object_content(&self.cfg.bucket_name, s3_key, ObjectContent::from(data))
            .send()
            .await
            .map_err(|err| S3Error::Sdk(err.to_string()))?;

        Ok(())
    }
}

fn is_bucket_already_exists_error(err: &MinioError) -> bool {
    if let MinioError::S3Error(resp) = err {
        return match &resp.code {
            ErrorCode::BucketAlreadyOwnedByYou => true,
            ErrorCode::OtherError(code) if code == "bucketalreadyexists" => true,
            _ => false,
        };
    }
    false
}

#[derive(Debug, Error)]
pub enum S3Error {
    #[error("S3 SDK error: {0}")]
    Sdk(String),
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
}


