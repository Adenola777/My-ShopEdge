# Setting up the file store

Written 28 September 2026 for an S3 bucket in London, and rewritten on 30 September 2026
when the owner ruled that AWS is not used for now and the store is a **Cloudflare R2 bucket
in the EU jurisdiction** (A10.8 as amended). The service code is `service/app/storage.py`.
It speaks the S3 protocol, so the same code serves R2 and AWS and only the settings differ.

It has run against a local stand-in for S3, configured as R2 will be
(`testdata/storage_check.py`, 11 of 11 on 30 September), and never against a real bucket.
The first real upload is its test.

Every step below happens in the Cloudflare dashboard or on Render. No key is ever typed into
a conversation.

## 1. The bucket

The owner created it on 30 September 2026 under R2 Object Storage, in the **EU**
jurisdiction. R2 buckets are private unless a public address is switched on, so leave
**Public access** off. R2 Data Catalog is not used.

## 2. Allow the browser to upload

A seller's browser uploads the cost file straight to the bucket through a URL the service
signs, and fetches exports the same way. The browser refuses to do either unless the bucket
names the site. Open the bucket, then **Settings**, then **CORS Policy**, and add:

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

The upload sends one header, `content-type`, at `web/src/components/SetupForms.jsx` line 218.

## 3. Create a key that can reach only this bucket

In R2, open **Manage API tokens** and create an API token with **Object Read & Write**
permission, applied to **this bucket only**. Cloudflare shows an **Access Key ID** and a
**Secret Access Key** once. They are the pair the service uses.

## 4. Give the service the settings

The bucket's **Settings** page shows its **S3 API** address. For an EU bucket it has the form
`https://{account id}.eu.r2.cloudflarestorage.com/{bucket}`. The endpoint below is that
address **without** the bucket name at the end.

On Render, open `My-ShopEdge-1`, then **Environment**, and add:

| Variable | Value |
|---|---|
| `S3_BUCKET` | the bucket name |
| `AWS_ENDPOINT_URL_S3` | the S3 API address without the bucket name |
| `AWS_REGION` | `auto` |
| `AWS_ACCESS_KEY_ID` | from step 3 |
| `AWS_SECRET_ACCESS_KEY` | from step 3 |

The variable names say AWS because boto3, the library that signs the URLs, reads them by
those names. Render redeploys on save. Until `S3_BUCKET` is set, a cost upload answers 503
`storage_unconfigured` and writes nothing.

## 5. Check it

Upload a small CSV on the cost screen. If the browser reports a CORS error, step 2 does not
name the address the site is served from. If the service answers 502 or logs an error from
botocore, the endpoint, the region or the key is wrong, and the Render log names which.
