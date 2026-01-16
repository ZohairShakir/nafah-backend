# Testing Guide

## Sample Data Files

Two sample CSV files are provided:

1. **`sample_sales_data.csv`** - Sales transactions from January to March 2024
   - 150+ transactions
   - 10 different products
   - Multiple categories (Food, Personal Care, Beverages, Snacks)
   - Good variety for testing analytics

2. **`sample_inventory_data.csv`** - Current inventory levels
   - 10 products matching sales data
   - Stock levels and unit costs
   - Needed for inventory velocity and profitability analytics

## Testing Steps

### 1. Start the Backend Server

```bash
cd backend
python run.py
```

Server will start at `http://127.0.0.1:8000`

### 2. Upload Sales Data

Using curl:
```bash
curl -X POST http://127.0.0.1:8000/api/v1/datasets \
  -F "file=@sample_sales_data.csv" \
  -F "name=Sample Sales Data Q1 2024"
```

Or using Python requests:
```python
import requests

with open('sample_sales_data.csv', 'rb') as f:
    response = requests.post(
        'http://127.0.0.1:8000/api/v1/datasets',
        files={'file': f},
        data={'name': 'Sample Sales Data Q1 2024'}
    )
    print(response.json())
```

Save the `dataset_id` from the response!

### 3. Upload Inventory Data (Optional)

```bash
curl -X POST http://127.0.0.1:8000/api/v1/datasets \
  -F "file=@sample_inventory_data.csv" \
  -F "name=Sample Inventory Data"
```

### 4. Test Analytics Endpoints

Replace `{dataset_id}` with the ID from step 2:

**Best Sellers:**
```bash
curl http://127.0.0.1:8000/api/v1/analytics/{dataset_id}/best-sellers?limit=10
```

**Revenue Contribution:**
```bash
curl http://127.0.0.1:8000/api/v1/analytics/{dataset_id}/revenue-contribution
```

**Trends:**
```bash
curl http://127.0.0.1:8000/api/v1/analytics/{dataset_id}/trends?metric=revenue&months=3
```

**Seasonality:**
```bash
curl http://127.0.0.1:8000/api/v1/analytics/{dataset_id}/seasonality
```

**Dead Stock:**
```bash
curl http://127.0.0.1:8000/api/v1/analytics/{dataset_id}/dead-stock?days_threshold=90
```

**Profitability:**
```bash
curl http://127.0.0.1:8000/api/v1/analytics/{dataset_id}/profitability
```

**Inventory Velocity:**
```bash
curl http://127.0.0.1:8000/api/v1/analytics/{dataset_id}/inventory-velocity
```

### 5. Generate Insights

```bash
curl -X POST http://127.0.0.1:8000/api/v1/insights/{dataset_id}/generate
```

### 6. Get Insights

```bash
curl http://127.0.0.1:8000/api/v1/insights/{dataset_id}
```

## Expected Results

### Best Sellers
- **Rice 5kg** should be #1 (highest quantity sold)
- **Tea 500g** should have high revenue

### Revenue Contribution
- Products should be ranked by total revenue
- Percentages should add up to 100%

### Trends
- Should show month-over-month changes
- February and March should show growth trends

### Seasonality
- Some products may show seasonal patterns
- Peak months should be identified

### Dead Stock
- Products with no recent sales will appear
- Days since last sale calculated

### Profitability
- Products ranked by profit margin
- Requires inventory data for cost calculation

## Using Swagger UI

1. Open browser: `http://127.0.0.1:8000/docs`
2. Try endpoints interactively
3. Upload files directly through the UI
4. See request/response schemas

## Troubleshooting

**No data returned:**
- Make sure dataset was uploaded successfully
- Check dataset status: `GET /api/v1/datasets/{id}`
- Verify data was stored in database

**Analytics errors:**
- Check that CSV has required columns
- Verify date format is correct
- Ensure numeric columns are valid numbers

**Cache issues:**
- Delete cache: Remove files from `data/parquet/`
- Or delete and re-upload dataset

## Sample Data Details

### Sales Data
- **Period**: January 15 - March 5, 2024
- **Products**: 10 items across 4 categories
- **Transactions**: 50+ unique transactions
- **Total Records**: 150+ sales records

### Inventory Data
- **Products**: 10 items matching sales data
- **Stock Levels**: Realistic quantities
- **Costs**: Unit costs for profit calculation

## Next Steps

1. Test with your own CSV files
2. Try different date ranges
3. Test edge cases (empty data, missing columns)
4. Integrate with Tauri frontend
