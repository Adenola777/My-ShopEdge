# Setting up the file store

Written 28 September 2026. The owner chose a private S3 bucket in London for cost uploads,
exports and the data download. The service code is `service/app/storage.py`. It has run
against a local stand-in for S3 and never against a real bucket, so the first real upload
is its test.

Every step below happens in the AWS console or in your own terminal. No key is ever typed
into a conversation.

## 1. Create the bucket

In the S3 console, create a bucket in **Europe (London) eu-west-2**. Keep **Block all
public access** switched on. Keep versioning off for now: Object Lock for the six-year
invoice store (A10.8) is a separate decision, and it can only be switched on when a bucket
is created, so if it will be wanted, choose it here.

## 2. Allow the browser to upload

A seller's browser uploads the cost file straight to the bucket through a URL the service
signs. The browser refuses to do that unless the bucket names the site. Under the bucket's
**Permissions**, set **Cross-origin resource sharing (CORS)** to the following, with the
site's real addresses in `AllowedOrigins`:

```json
[
  {
    "AllowedOrigins": ["https://my-shop-edge.vercel.app"],
    "AllowedMethods": ["PUT", "GET"],
    "AllowedHeaders": ["Content-Type"],
    "MaxAgeSeconds": 600
  }
]
```

## 3. Create a key that can reach only this bucket

In IAM, create a user for the service with no console access, and attach a policy that
allows only reading and writing objects in this bucket:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": "arn:aws:s3:::BUCKET_NAME/*"
    }
  ]
}
```

Create an access key for that user. AWS shows the secret once.

## 4. Give the service the settings

On Render, open `My-ShopEdge-1`, then **Environment**, and add:

| Variable | Value |
|---|---|
| `S3_BUCKET` | the bucket name |
| `AWS_REGION` | `eu-west-2` |
| `AWS_ACCESS_KEY_ID` | from step 3 |
| `AWS_SECRET_ACCESS_KEY` | from step 3 |

Render redeploys on save. Until `S3_BUCKET` is set, a cost upload answers 503
`storage_unconfigured` and writes nothing.

## 5. Check it

Upload a small CSV through the cost upload screen once it is built, or with the API. If the
browser reports a CORS error, step 2 does not name the address the site is served from.
