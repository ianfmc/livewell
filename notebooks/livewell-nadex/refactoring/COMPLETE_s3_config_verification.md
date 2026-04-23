# S3 Configuration Verification Report

## Configuration File: `configs/s3.yaml`
```yaml
bucket: nadex-daily-results
public_bucket: market-data-prod.nadex.com
region: us-west-2
prefixes:
  historical: historical
  manifests: manifests
  logs: logs
mapping_file: contracts.csv
```

## Usage in `nadex-recommendation.ipynb`

### ✅ Configuration Values Being Used

| Config Key | Config Value | Variable Name | Where Used |
|-----------|--------------|---------------|------------|
| `bucket` | `nadex-daily-results` | `BUCKET` | • `run_recommendation_pipeline(bucket_name=BUCKET)`<br>• `append_runlog_s3(BUCKET, ...)` |
| `region` | `us-west-2` | `REGION` | • `run_recommendation_pipeline(region=REGION)`<br>• `create_s3_clients(region=region)`<br>• `upload_df_to_s3(..., region=region)`<br>• `boto3.Session(region_name=cfg.get('region'))` |
| `prefixes.logs` | `logs` | `RUNLOG_KEY` | • `append_runlog_s3(BUCKET, RUNLOG_KEY, ...)` |
| `mapping_file` | `contracts.csv` | `MAPPING_FILE` | • `run_recommendation_pipeline(mapping_file=MAPPING_FILE)`<br>• `load_strikes(mapping_file)` |

### ⚠️ Configuration Value with Default Fallback

| Config Key | Lookup | Result | Variable Name | Where Used |
|-----------|--------|--------|---------------|------------|
| `prefixes.recommendations` | `cfg['prefixes'].get('recommendations', 'recommendations')` | **'recommendations'** (using default) | `RECS_PREFIX` | • Used in S3 key: `f"{RECS_PREFIX}/{today_str}.csv"` |

**Note:** The `s3.yaml` file defines `prefixes.historical` but the code looks for `prefixes.recommendations`. Since it doesn't exist, it uses the default value 'recommendations'. 

**Recommendation:** If you want to use the 'historical' prefix for recommendations, either:
1. Update s3.yaml: Change `historical:` to `recommendations:`, OR
2. Update notebook: Change `RECS_PREFIX = cfg['prefixes'].get('historical', 'recommendations')`

### ❌ Configuration Values NOT Currently Used

| Config Key | Config Value | Status |
|-----------|--------------|--------|
| `public_bucket` | `market-data-prod.nadex.com` | **Not used in notebook** |
| `prefixes.historical` | `historical` | **Not used (code looks for 'recommendations' instead)** |
| `prefixes.manifests` | `manifests` | **Not used in notebook** |

## Summary

### ✅ WORKING CORRECTLY:
1. ✅ **bucket** → `BUCKET` → Used throughout notebook
2. ✅ **region** → `REGION` → Passed to all S3 functions
3. ✅ **prefixes.logs** → `RUNLOG_KEY` → Used for run logging
4. ✅ **mapping_file** → `MAPPING_FILE` → Used to load contracts

### ⚠️ MINOR ISSUE:
- **prefixes.recommendations** doesn't exist in s3.yaml, so it defaults to 'recommendations'
- Your s3.yaml has `prefixes.historical` but your code expects `prefixes.recommendations`

### ℹ️ UNUSED CONFIG VALUES:
- **public_bucket**: Defined but not referenced in the notebook
- **prefixes.historical**: Defined but code looks for 'recommendations' instead
- **prefixes.manifests**: Defined but not used

## Recommendation

To fully align your configuration with your code, update `configs/s3.yaml`:

```yaml
bucket: nadex-daily-results
public_bucket: market-data-prod.nadex.com  # Optional: can remove if not needed
region: us-west-2
prefixes:
  recommendations: recommendations  # Changed from 'historical'
  manifests: manifests              # Keep if needed for other scripts
  logs: logs
mapping_file: contracts.csv
```

Or alternatively, update the notebook to use 'historical':
```python
RECS_PREFIX = cfg['prefixes'].get('historical', 'recommendations')
```
