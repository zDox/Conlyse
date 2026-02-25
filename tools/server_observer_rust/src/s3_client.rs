use aws_config::BehaviorVersion;
use aws_config::Region;
use aws_credential_types::Credentials;
use aws_sdk_s3::{config::Builder as S3ConfigBuilder, primitives::ByteStream, Client};
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
        let region = Region::new(cfg.region.clone());
        let shared = aws_config::defaults(BehaviorVersion::latest())
            .region(region)
            .load()
            .await;

        let creds = Credentials::new(
            cfg.access_key.clone(),
            cfg.secret_key.clone(),
            None,
            None,
            "static",
        );
        let s3_conf = S3ConfigBuilder::from(&shared)
            .endpoint_url(cfg.endpoint_url.clone())
            .credentials_provider(creds)
            .build();

        let client = Client::from_conf(s3_conf);
        let s3 = Self { cfg, client };

        // Ensure bucket exists on startup.
        s3.ensure_bucket_exists().await?;

        Ok(s3)
    }

    async fn ensure_bucket_exists(&self) -> Result<(), S3Error> {
        let head = self
            .client
            .head_bucket()
            .bucket(&self.cfg.bucket_name)
            .send()
            .await;

        if head.is_ok() {
            return Ok(());
        }

        // Try to create if head failed
        self.client
            .create_bucket()
            .bucket(&self.cfg.bucket_name)
            .send()
            .await
            .map_err(|e| S3Error::Sdk(e.to_string()))?;

        Ok(())
    }

    pub async fn upload_file<P: AsRef<Path>>(
        &self,
        local_path: P,
        s3_key: &str,
    ) -> Result<(), S3Error> {
        let path = local_path.as_ref();
        let data = tokio::fs::read(path).await?;
        let body = ByteStream::from(data);

        self.client
            .put_object()
            .bucket(&self.cfg.bucket_name)
            .key(s3_key)
            .body(body)
            .send()
            .await
            .map_err(|e| S3Error::Sdk(e.to_string()))?;

        Ok(())
    }
}

#[derive(Debug, Error)]
pub enum S3Error {
    #[error("S3 SDK error: {0}")]
    Sdk(String),
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
}


