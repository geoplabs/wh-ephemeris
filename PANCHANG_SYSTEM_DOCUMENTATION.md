# 📚 Panchang System Documentation

## Overview

The WH-Ephemeris API provides comprehensive Vedic calendar (Panchang) calculations and astrological services. This documentation covers all available endpoints for integration with whathoroscope.com and other applications.

## 🌟 Core Features

- **Panchang Calculations**: Tithi, Nakshatra, Yoga, Karana, Rashi
- **Muhurta Analysis**: Auspicious timing calculations
- **Multi-language Support**: Hindi, English, Sanskrit with multiple scripts
- **Chart Generation**: Vedic and Western astrological charts
- **Transit Analysis**: Planetary movement calculations
- **Compatibility Analysis**: Relationship compatibility reports
- **Remedies Engine**: Personalized astrological remedies
- **Forecast Generation**: Daily, monthly, and yearly predictions

---

## 🔐 Authentication

All API endpoints require authentication using API keys:

```bash
# Header-based authentication
Authorization: Bearer YOUR_API_KEY

# Example
curl -H "Authorization: Bearer pHSbj2vjJ+rUprhF2W2B3acz6QCLdEOdFmb1yzuGWPE=" \
  "https://api.whathoroscope.com/v1/panchang/today?lat=28.6139&lon=77.2090"
```

---

## 📡 API Endpoints

### 🏥 Health & System

#### GET /health
System health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "1.0.0"
}
```

#### GET /docs
Interactive API documentation (Swagger UI).

#### GET /redoc
Alternative API documentation (ReDoc).

---

### 📅 Panchang (Vedic Calendar)

#### GET /v1/panchang/today
Get today's Panchang for a specific location.

**Parameters:**
- `lat` (required): Latitude (-90 to 90)
- `lon` (required): Longitude (-180 to 180)
- `tz` (optional): Timezone (default: auto-detected)
- `ayanamsha` (optional): Ayanamsha system (default: "lahiri")
- `include_muhurta` (optional): Include Muhurta timings (default: true)
- `include_hora` (optional): Include Hora calculations (default: false)
- `lang` (optional): Language code ("en", "hi", "sa")
- `script` (optional): Script ("latn", "deva", "iast")
- `show_bilingual` (optional): Show bilingual labels (default: false)
- `place_label` (optional): Custom place name

**Example:**
```bash
curl "https://api.whathoroscope.com/v1/panchang/today?lat=28.6139&lon=77.2090&lang=hi&script=deva" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

**Response:**
```json
{
  "date": "2024-01-15",
  "location": {
    "latitude": 28.6139,
    "longitude": 77.2090,
    "timezone": "Asia/Kolkata",
    "place_label": "New Delhi"
  },
  "panchang": {
    "tithi": {
      "name": "Shukla Panchami",
      "name_hi": "शुक्ल पंचमी",
      "number": 5,
      "paksha": "shukla",
      "end_time": "2024-01-15T14:23:45+05:30"
    },
    "nakshatra": {
      "name": "Rohini",
      "name_hi": "रोहिणी",
      "number": 4,
      "lord": "Moon",
      "end_time": "2024-01-15T18:45:12+05:30"
    },
    "yoga": {
      "name": "Siddha",
      "name_hi": "सिद्ध",
      "number": 21,
      "end_time": "2024-01-15T11:30:22+05:30"
    },
    "karana": {
      "name": "Bava",
      "name_hi": "बव",
      "number": 1,
      "end_time": "2024-01-15T14:23:45+05:30"
    },
    "rashi": {
      "name": "Vrishabha",
      "name_hi": "वृषभ",
      "number": 2,
      "lord": "Venus"
    }
  },
  "muhurta": {
    "abhijit": {
      "start": "2024-01-15T11:45:30+05:30",
      "end": "2024-01-15T12:33:15+05:30",
      "duration_minutes": 47.75
    },
    "brahma": {
      "start": "2024-01-15T06:12:45+05:30",
      "end": "2024-01-15T07:00:30+05:30",
      "duration_minutes": 47.75
    }
  },
  "sunrise": "2024-01-15T07:12:34+05:30",
  "sunset": "2024-01-15T17:45:22+05:30",
  "moonrise": "2024-01-15T09:23:11+05:30",
  "moonset": "2024-01-15T21:34:56+05:30"
}
```

#### POST /v1/panchang/compute
Calculate Panchang for a specific date and location.

**Request Body:**
```json
{
  "date": "2024-01-15",
  "latitude": 28.6139,
  "longitude": 77.2090,
  "timezone": "Asia/Kolkata",
  "ayanamsha": "lahiri",
  "include_muhurta": true,
  "include_hora": false,
  "lang": "en",
  "script": "latn",
  "show_bilingual": false,
  "place_label": "New Delhi"
}
```

**Response:** Same as GET /v1/panchang/today

#### POST /v1/panchang/report
Generate a detailed PDF Panchang report.

**Request Body:**
```json
{
  "date": "2024-01-15",
  "latitude": 28.6139,
  "longitude": 77.2090,
  "timezone": "Asia/Kolkata",
  "lang": "hi",
  "script": "deva",
  "include_festivals": true,
  "include_muhurta": true,
  "include_remedies": true
}
```

**Response:**
```json
{
  "report_id": "panchang_20240115_delhi_hi",
  "download_url": "https://api.whathoroscope.com/reports/panchang_20240115_delhi_hi.pdf",
  "expires_at": "2024-01-22T10:30:00Z"
}
```

---

### 🎯 Chart Calculations

#### POST /v1/charts/natal
Generate natal chart calculations.

**Request Body:**
```json
{
  "birth_date": "1990-05-15",
  "birth_time": "14:30:00",
  "latitude": 28.6139,
  "longitude": 77.2090,
  "timezone": "Asia/Kolkata",
  "chart_type": "vedic",
  "house_system": "whole_sign",
  "ayanamsha": "lahiri",
  "include_aspects": true,
  "include_dignities": true
}
```

**Response:**
```json
{
  "chart_id": "natal_19900515_1430_delhi",
  "birth_info": {
    "date": "1990-05-15",
    "time": "14:30:00",
    "location": "New Delhi",
    "coordinates": [28.6139, 77.2090]
  },
  "planets": {
    "sun": {
      "longitude": 54.23,
      "sign": "Taurus",
      "house": 7,
      "nakshatra": "Rohini",
      "dignity": "neutral"
    },
    "moon": {
      "longitude": 123.45,
      "sign": "Cancer",
      "house": 10,
      "nakshatra": "Pushya",
      "dignity": "exalted"
    }
  },
  "houses": {
    "1": {
      "sign": "Scorpio",
      "lord": "Mars",
      "cusp": 234.56
    }
  },
  "aspects": [
    {
      "planet1": "sun",
      "planet2": "moon",
      "aspect": "trine",
      "orb": 2.34,
      "applying": true
    }
  ]
}
```

#### POST /v1/charts/transit
Calculate current transits for a natal chart.

**Request Body:**
```json
{
  "natal_chart_id": "natal_19900515_1430_delhi",
  "transit_date": "2024-01-15",
  "transit_time": "10:30:00",
  "timezone": "Asia/Kolkata",
  "include_aspects": true
}
```

---

### 🔄 Dashas

#### POST /v1/dashas/vimshottari
Calculate Vimshottari Dasha periods.

**Request Body:**
```json
{
  "birth_date": "1990-05-15",
  "birth_time": "14:30:00",
  "latitude": 28.6139,
  "longitude": 77.2090,
  "timezone": "Asia/Kolkata",
  "ayanamsha": "lahiri",
  "start_date": "2024-01-01",
  "end_date": "2030-12-31"
}
```

**Response:**
```json
{
  "birth_moon_nakshatra": "Pushya",
  "birth_moon_position": 123.45,
  "current_dasha": {
    "mahadasha": {
      "planet": "Jupiter",
      "start": "2020-03-15T00:00:00Z",
      "end": "2036-03-15T00:00:00Z",
      "duration_years": 16
    },
    "antardasha": {
      "planet": "Saturn",
      "start": "2023-07-20T00:00:00Z",
      "end": "2026-01-15T00:00:00Z",
      "duration_years": 2.49
    },
    "pratyantardasha": {
      "planet": "Mercury",
      "start": "2024-01-01T00:00:00Z",
      "end": "2024-05-18T00:00:00Z",
      "duration_days": 138
    }
  },
  "upcoming_periods": [
    {
      "level": "pratyantardasha",
      "planet": "Ketu",
      "start": "2024-05-18T00:00:00Z",
      "end": "2024-08-25T00:00:00Z"
    }
  ]
}
```

---

### 🌟 Transits

#### POST /v1/transits/current
Get current planetary transits.

**Request Body:**
```json
{
  "date": "2024-01-15",
  "time": "10:30:00",
  "latitude": 28.6139,
  "longitude": 77.2090,
  "timezone": "Asia/Kolkata",
  "ayanamsha": "lahiri",
  "include_aspects": true,
  "natal_planets": {
    "sun": 54.23,
    "moon": 123.45
  }
}
```

#### POST /v1/transits/forecast
Generate transit forecast for a period.

**Request Body:**
```json
{
  "natal_chart_id": "natal_19900515_1430_delhi",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "significant_only": true,
  "include_retrograde": true
}
```

---

### 💕 Compatibility

#### POST /v1/compatibility/synastry
Calculate relationship compatibility between two charts.

**Request Body:**
```json
{
  "person1": {
    "birth_date": "1990-05-15",
    "birth_time": "14:30:00",
    "latitude": 28.6139,
    "longitude": 77.2090,
    "timezone": "Asia/Kolkata"
  },
  "person2": {
    "birth_date": "1992-08-22",
    "birth_time": "09:15:00",
    "latitude": 19.0760,
    "longitude": 72.8777,
    "timezone": "Asia/Kolkata"
  },
  "analysis_type": "vedic",
  "include_guna_milan": true,
  "include_mangal_dosha": true
}
```

**Response:**
```json
{
  "compatibility_score": 85.5,
  "guna_milan": {
    "total_points": 28,
    "max_points": 36,
    "percentage": 77.8,
    "gunas": {
      "varna": {"points": 1, "max": 1},
      "vashya": {"points": 2, "max": 2},
      "tara": {"points": 3, "max": 3},
      "yoni": {"points": 4, "max": 4},
      "graha_maitri": {"points": 5, "max": 5},
      "gana": {"points": 6, "max": 6},
      "bhakoot": {"points": 7, "max": 7},
      "nadi": {"points": 0, "max": 8}
    }
  },
  "mangal_dosha": {
    "person1_dosha": false,
    "person2_dosha": true,
    "severity": "mild",
    "remedies_required": true
  },
  "planetary_compatibility": {
    "sun_moon": "excellent",
    "moon_moon": "good",
    "venus_mars": "challenging"
  }
}
```

---

### 🔮 Remedies

#### POST /v1/remedies/generate
Generate personalized astrological remedies.

**Request Body:**
```json
{
  "birth_date": "1990-05-15",
  "birth_time": "14:30:00",
  "latitude": 28.6139,
  "longitude": 77.2090,
  "timezone": "Asia/Kolkata",
  "concerns": ["career", "health", "relationships"],
  "remedy_types": ["gemstone", "mantra", "yantra", "charity"],
  "budget_range": "medium",
  "lang": "en"
}
```

**Response:**
```json
{
  "remedies": [
    {
      "type": "gemstone",
      "recommendation": "Blue Sapphire",
      "reason": "Strengthen Saturn for career growth",
      "weight": "3-5 carats",
      "metal": "Silver or White Gold",
      "finger": "Middle finger, right hand",
      "day_to_wear": "Saturday",
      "mantra": "Om Sham Shanicharaya Namah"
    },
    {
      "type": "mantra",
      "recommendation": "Gayatri Mantra",
      "repetitions": 108,
      "timing": "Sunrise",
      "duration": "40 days",
      "benefits": "Overall spiritual growth and protection"
    }
  ],
  "priority_order": ["gemstone", "mantra", "charity"],
  "total_estimated_cost": "$150-300"
}
```

---

### 📊 Forecasts

#### POST /v1/forecasts/daily
Generate daily forecast.

**Request Body:**
```json
{
  "birth_date": "1990-05-15",
  "birth_time": "14:30:00",
  "latitude": 28.6139,
  "longitude": 77.2090,
  "timezone": "Asia/Kolkata",
  "forecast_date": "2024-01-15",
  "areas": ["career", "love", "health", "finance"],
  "lang": "en"
}
```

#### POST /v1/forecasts/monthly
Generate monthly forecast.

**Request Body:**
```json
{
  "birth_date": "1990-05-15",
  "birth_time": "14:30:00",
  "latitude": 28.6139,
  "longitude": 77.2090,
  "timezone": "Asia/Kolkata",
  "month": "2024-01",
  "include_weekly_breakdown": true,
  "lang": "en"
}
```

#### POST /v1/forecasts/yearly
Generate yearly forecast.

**Request Body:**
```json
{
  "birth_date": "1990-05-15",
  "birth_time": "14:30:00",
  "latitude": 28.6139,
  "longitude": 77.2090,
  "timezone": "Asia/Kolkata",
  "year": 2024,
  "include_monthly_breakdown": true,
  "lang": "en"
}
```

---

### 🎭 Interpretations

#### POST /v1/interpret/natal
Get detailed natal chart interpretation.

**Request Body:**
```json
{
  "birth_date": "1990-05-15",
  "birth_time": "14:30:00",
  "latitude": 28.6139,
  "longitude": 77.2090,
  "timezone": "Asia/Kolkata",
  "interpretation_style": "vedic",
  "include_remedies": true,
  "lang": "en"
}
```

#### POST /v1/interpret/transit
Interpret current transits.

**Request Body:**
```json
{
  "natal_chart_id": "natal_19900515_1430_delhi",
  "transit_date": "2024-01-15",
  "significant_transits_only": true,
  "lang": "en"
}
```

---

### 📋 Full Reports & Analytics

#### POST /v1/reports/full-natal
Generate comprehensive natal report.

**Request Body:**
```json
{
  "birth_date": "1990-05-15",
  "birth_time": "14:30:00",
  "latitude": 28.6139,
  "longitude": 77.2090,
  "timezone": "Asia/Kolkata",
  "name": "John Doe",
  "report_type": "detailed",
  "include_charts": true,
  "include_remedies": true,
  "lang": "en",
  "format": "pdf"
}
```

#### POST /v1/reports/compatibility
Generate detailed compatibility report.

**Request Body:**
```json
{
  "person1": {
    "name": "Person A",
    "birth_date": "1990-05-15",
    "birth_time": "14:30:00",
    "latitude": 28.6139,
    "longitude": 77.2090,
    "timezone": "Asia/Kolkata"
  },
  "person2": {
    "name": "Person B",
    "birth_date": "1992-08-22",
    "birth_time": "09:15:00",
    "latitude": 19.0760,
    "longitude": 72.8777,
    "timezone": "Asia/Kolkata"
  },
  "report_type": "comprehensive",
  "include_remedies": true,
  "lang": "en",
  "format": "pdf"
}
```

---

### 📁 Report Management

#### GET /v1/reports/{report_id}
Download a generated report.

**Parameters:**
- `report_id`: Unique report identifier

**Response:** Binary PDF file or JSON with download URL

#### GET /v1/reports/{report_id}/status
Check report generation status.

**Response:**
```json
{
  "report_id": "natal_20240115_johndoe",
  "status": "completed",
  "progress": 100,
  "download_url": "https://api.whathoroscope.com/reports/natal_20240115_johndoe.pdf",
  "expires_at": "2024-01-22T10:30:00Z"
}
```

---

## 🌍 Panchang-Specific API Endpoints Summary

For **whathoroscope.com** Panchang page integration, these are the key endpoints:

### Primary Panchang Endpoints:

1. **GET /v1/panchang/today** - Today's Panchang
   - Most commonly used for current day display
   - Supports all languages and scripts

2. **POST /v1/panchang/compute** - Custom date Panchang
   - For historical or future date calculations
   - Same response format as today endpoint

3. **POST /v1/panchang/report** - PDF Panchang report
   - For downloadable detailed reports
   - Includes festivals and remedies

### Supporting Endpoints:

4. **GET /health** - System status check
5. **POST /v1/remedies/generate** - Panchang-based remedies
6. **POST /v1/forecasts/daily** - Daily predictions based on Panchang

### Integration Examples:

```javascript
// Today's Panchang for Delhi
const panchang = await fetch('/v1/panchang/today?lat=28.6139&lon=77.2090&lang=hi&script=deva');

// Custom date Panchang
const customPanchang = await fetch('/v1/panchang/compute', {
  method: 'POST',
  body: JSON.stringify({
    date: '2024-01-15',
    latitude: 28.6139,
    longitude: 77.2090,
    lang: 'hi',
    script: 'deva'
  })
});

// Generate PDF report
const report = await fetch('/v1/panchang/report', {
  method: 'POST',
  body: JSON.stringify({
    date: '2024-01-15',
    latitude: 28.6139,
    longitude: 77.2090,
    lang: 'hi',
    include_festivals: true
  })
});
```

---

## 🔧 Configuration Parameters

### Ayanamsha Options:
- `lahiri` (default) - Lahiri/Chitrapaksha
- `raman` - B.V. Raman
- `krishnamurti` - K.P. System
- `yukteshwar` - Sri Yukteshwar

### Language Codes:
- `en` - English
- `hi` - Hindi  
- `sa` - Sanskrit
- `bn` - Bengali
- `ta` - Tamil
- `te` - Telugu
- `kn` - Kannada
- `ml` - Malayalam
- `gu` - Gujarati
- `mr` - Marathi
- `or` - Odia
- `pa` - Punjabi

### Script Options:
- `latn` - Latin/Roman script
- `deva` - Devanagari script
- `iast` - International Alphabet of Sanskrit Transliteration

### House Systems:
- `whole_sign` (Vedic default)
- `placidus` (Western default)
- `koch`
- `equal`
- `campanus`

---

## 🚨 Error Handling

### Common Error Responses:

```json
{
  "error": {
    "code": "INVALID_COORDINATES",
    "message": "Latitude must be between -90 and 90 degrees",
    "details": {
      "field": "latitude",
      "value": 95.5,
      "constraint": "range(-90, 90)"
    }
  }
}
```

### HTTP Status Codes:
- `200` - Success
- `400` - Bad Request (invalid parameters)
- `401` - Unauthorized (missing/invalid API key)
- `403` - Forbidden (rate limit exceeded)
- `404` - Not Found (invalid endpoint)
- `422` - Unprocessable Entity (validation errors)
- `429` - Too Many Requests (rate limiting)
- `500` - Internal Server Error
- `503` - Service Unavailable

---

## 📈 Rate Limiting

- **Default**: 60 requests per minute per API key
- **Burst**: Up to 10 requests per second
- **Headers**: 
  - `X-RateLimit-Limit`: Total requests allowed
  - `X-RateLimit-Remaining`: Requests remaining
  - `X-RateLimit-Reset`: Reset timestamp

---

## 🔍 Testing

### Health Check:
```bash
curl https://api.whathoroscope.com/health
```

### Sample Panchang Request:
```bash
curl "https://api.whathoroscope.com/v1/panchang/today?lat=28.6139&lon=77.2090" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json"
```

---

## 📞 Support & Integration

For integration support with whathoroscope.com:
- API documentation: `/docs` endpoint
- Rate limiting: Contact for higher limits
- Custom endpoints: Available for specific requirements
- Webhook support: Available for real-time updates

---

**This API provides comprehensive Vedic calendar and astrological services optimized for whathoroscope.com integration with multi-language support and detailed calculations.** 🌟
