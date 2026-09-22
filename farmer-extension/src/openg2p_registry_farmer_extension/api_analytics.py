import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from openg2p_fastapi_common.context import dbengine
from sqlalchemy import text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/farmer-registry/analytics", tags=["Farmer Registry Analytics"])

SCOPE = """
  WITH scope AS (
    SELECT
      f.internal_record_id,
      f.internal_record_id AS farmer_uuid,
      (SELECT elem->>'level_value_id' FROM jsonb_array_elements(f.geo_code_hierarchy_json->'hierarchy') elem WHERE elem->>'level_mnemonic' = 'region' LIMIT 1) AS region,
      (SELECT elem->>'level_value_id' FROM jsonb_array_elements(f.geo_code_hierarchy_json->'hierarchy') elem WHERE elem->>'level_mnemonic' = 'zone' LIMIT 1) AS zone,
      (SELECT elem->>'level_value_id' FROM jsonb_array_elements(f.geo_code_hierarchy_json->'hierarchy') elem WHERE elem->>'level_mnemonic' = 'woreda' LIMIT 1) AS woreda,
      (SELECT elem->>'level_value_id' FROM jsonb_array_elements(f.geo_code_hierarchy_json->'hierarchy') elem WHERE elem->>'level_mnemonic' = 'kebele' LIMIT 1) AS kebele,
      f.state,
      f.gender,
      f.education_level,
      f.is_psnp_user,
      f.import_source,
      f.land_ownership,
      f.created_at::date AS recorded_on,
      f.is_household_head,
      f.total_land_area,
      f.foundational_id,
      CASE 
        WHEN f.estimated_age < 18 THEN '0-18'
        WHEN f.estimated_age BETWEEN 18 AND 29 THEN '18-30'
        WHEN f.estimated_age BETWEEN 30 AND 49 THEN '30-50'
        WHEN f.estimated_age BETWEEN 50 AND 69 THEN '50-70'
        WHEN f.estimated_age >= 70 THEN '70+'
        ELSE 'Unknown'
      END AS age_group
    FROM g2p_register_farmers f
    WHERE f.record_status = 'ACTIVE'
      {DYNAMIC_FILTERS}
  )
"""

def build_where_clause(region, zone, woreda, kebele, record_state):
    conditions = []
    params = {}
    
    if region and region != 'all':
        conditions.append("f.geo_code_hierarchy_json @> jsonb_build_object('hierarchy', jsonb_build_array(jsonb_build_object('level_mnemonic', 'region', 'level_value_id', :region::text)))")
        params['region'] = region
    if zone and zone != 'all':
        conditions.append("f.geo_code_hierarchy_json @> jsonb_build_object('hierarchy', jsonb_build_array(jsonb_build_object('level_mnemonic', 'zone', 'level_value_id', :zone::text)))")
        params['zone'] = zone
    if woreda and woreda != 'all':
        conditions.append("f.geo_code_hierarchy_json @> jsonb_build_object('hierarchy', jsonb_build_array(jsonb_build_object('level_mnemonic', 'woreda', 'level_value_id', :woreda::text)))")
        params['woreda'] = woreda
    if kebele and kebele != 'all':
        conditions.append("f.geo_code_hierarchy_json @> jsonb_build_object('hierarchy', jsonb_build_array(jsonb_build_object('level_mnemonic', 'kebele', 'level_value_id', :kebele::text)))")
        params['kebele'] = kebele
    if record_state and record_state != 'all':
        conditions.append("COALESCE(f.state, 'ACTIVE') = :record_state")
        params['record_state'] = record_state

    clause = ""
    if conditions:
        clause = "AND " + " AND ".join(conditions)
        
    return clause, params

def farmers_by_level(level):
    return f"""
    {SCOPE}
    SELECT
      s.{level} AS {level}_id,
      COUNT(DISTINCT s.farmer_uuid)::integer AS farmers
    FROM scope s
    GROUP BY 1
    ORDER BY farmers DESC
    """

CHART_QUERIES = {
    'farmerKpis': f"""
    {SCOPE}
    SELECT
      COUNT(DISTINCT s.farmer_uuid)::integer AS total_farmers,
      COUNT(DISTINCT CASE WHEN s.gender = 'FEMALE' THEN s.farmer_uuid END)::integer AS female_farmers,
      COUNT(DISTINCT CASE WHEN s.gender = 'MALE' THEN s.farmer_uuid END)::integer AS male_farmers,
      COUNT(DISTINCT CASE WHEN s.is_household_head = true THEN s.farmer_uuid END)::integer AS household_heads,
      COALESCE(SUM(s.total_land_area), 0) AS total_land_size,
      COALESCE(AVG(s.total_land_area), 0) AS avg_farm_size,
      COUNT(DISTINCT CASE WHEN s.land_ownership = 'OWNER' THEN s.farmer_uuid END)::integer AS farmers_with_owned_land,
      COUNT(DISTINCT CASE WHEN s.foundational_id IS NOT NULL THEN s.farmer_uuid END)::integer AS farmers_with_id,
      COUNT(DISTINCT s.woreda)::integer AS woredas_reporting
    FROM scope s
    """,
    'farmersByFarmerId': f"""
    {SCOPE}
    SELECT
      'farmer_id' AS category,
      COUNT(DISTINCT CASE WHEN s.foundational_id IS NOT NULL THEN s.farmer_uuid END)::integer AS farmers
    FROM scope s
    """,
    'farmersByRecordState': f"""
    {SCOPE}
    SELECT
      CASE 
        WHEN s.state = 'APPROVED' THEN 'active'
        WHEN s.state = 'REJECTED' THEN 'rejected'
        ELSE COALESCE(s.state, 'open')
      END AS record_state,
      COUNT(DISTINCT s.farmer_uuid)::integer AS farmers
    FROM scope s
    GROUP BY 1
    """,
    'farmersByRegion': farmers_by_level('region'),
    'farmersByZone': farmers_by_level('zone'),
    'farmersByWoreda': farmers_by_level('woreda'),
    'farmersByKebele': farmers_by_level('kebele'),
    'farmersByType': f"""
    {SCOPE}
    SELECT
      COALESCE(s.land_ownership, 'Unknown') AS farming_type,
      COUNT(DISTINCT s.farmer_uuid)::integer AS farmers
    FROM scope s
    GROUP BY 1
    ORDER BY farmers DESC
    """,
    'farmersByAgeAndGender': f"""
    {SCOPE}
    SELECT
      s.age_group,
      COALESCE(s.gender, 'Unknown') AS gender,
      COUNT(DISTINCT s.farmer_uuid)::integer AS farmers
    FROM scope s
    GROUP BY 1, 2
    ORDER BY farmers DESC
    """,
    'farmersByEducation': f"""
    {SCOPE}
    SELECT
      COALESCE(s.education_level, 'Unknown') AS education,
      COUNT(DISTINCT s.farmer_uuid)::integer AS farmers
    FROM scope s
    GROUP BY 1
    ORDER BY farmers DESC
    """,
    'farmersBySupportStatus': f"""
    {SCOPE}
    SELECT
      CASE WHEN s.is_psnp_user THEN 'PSNP' ELSE 'Non-PSNP' END AS support_status,
      COUNT(DISTINCT s.farmer_uuid)::integer AS farmers
    FROM scope s
    GROUP BY 1
    ORDER BY farmers DESC
    """,
    'farmersByImportStatus': f"""
    {SCOPE}
    SELECT
      COALESCE(s.import_source, 'Manual') AS import_status,
      COUNT(DISTINCT s.farmer_uuid)::integer AS farmers
    FROM scope s
    GROUP BY 1
    ORDER BY farmers DESC
    """,
    'landTenureSplit': f"""
    {SCOPE}
    SELECT
      COALESCE(s.land_ownership, 'Unknown') AS ownership_type,
      COUNT(DISTINCT s.farmer_uuid)::integer AS parcels,
      COALESCE(SUM(s.total_land_area), 0) AS area
    FROM scope s
    GROUP BY 1
    ORDER BY parcels DESC
    """,
    'registryTrendByMonth': f"""
    {SCOPE}
    SELECT
      TO_CHAR(DATE_TRUNC('month', s.recorded_on), 'YYYY-MM') AS period,
      COUNT(DISTINCT s.farmer_uuid)::integer AS farmers
    FROM scope s
    WHERE s.recorded_on IS NOT NULL
    GROUP BY 1
    ORDER BY 1
    """,
    'registryCoverage': f"""
    {SCOPE}
    SELECT
      COUNT(DISTINCT s.farmer_uuid)::integer AS farmers
    FROM scope s
    """
}

@router.get("/charts")
async def get_chart_group(
    charts: str = Query(..., description="Comma separated list of chart names"),
    region: Optional[str] = 'all',
    zone: Optional[str] = 'all',
    woreda: Optional[str] = 'all',
    kebele: Optional[str] = 'all',
    recordState: Optional[str] = 'all'
):
    chart_names = charts.split(',')
    
    clause, params = build_where_clause(region, zone, woreda, kebele, recordState)
    
    results = {}
    
    async with dbengine.get_engine().connect() as conn:
        for chart_name in chart_names:
            if chart_name not in CHART_QUERIES:
                results[chart_name] = {
                    "success": False,
                    "error": "Chart not found",
                    "data": []
                }
                continue
                
            query_str = CHART_QUERIES[chart_name].replace('{DYNAMIC_FILTERS}', clause)
            
            try:
                result = await conn.execute(text(query_str), params)
                rows = [dict(r._mapping) for r in result]
                
                # Convert decimal to float and bigint to int for JSON serialization
                for row in rows:
                    for k, v in row.items():
                        if hasattr(v, '__float__') and not isinstance(v, (int, float, bool, str, type(None))):
                            row[k] = float(v)
                
                results[chart_name] = {
                    "success": True,
                    "data": rows,
                    "error": None
                }
            except Exception as e:
                logger.error(f"Error executing chart query {chart_name}: {e}")
                results[chart_name] = {
                    "success": False,
                    "data": [],
                    "error": str(e)
                }
                
    return {
        "success": True,
        "data": results,
        "error": None,
        "summary": {
            "total": len(chart_names),
            "successful": sum(1 for c in results.values() if c["success"]),
            "failed": sum(1 for c in results.values() if not c["success"]),
            "totalExecutionTime": 0
        }
    }
@router.get("/filter-options")
async def get_filter_options():
    try:
        async with dbengine.get_engine().connect() as conn:
            # Regions
            res = await conn.execute(text("" "
                SELECT DISTINCT elem->>'level_value_id' AS code, elem->>'level_value_id' AS id, elem->>'level_value_id' AS name
                FROM g2p_register_farmers f, jsonb_array_elements(f.geo_code_hierarchy_json->'hierarchy') elem 
                WHERE elem->>'level_mnemonic' = 'region' AND f.record_status = 'ACTIVE'
            " ""))
            regions = [dict(r._mapping) for r in res]
            
            # Record States
            res = await conn.execute(text("" "
                SELECT f.state AS code, f.state AS name, COUNT(*)::integer AS count
                FROM g2p_register_farmers f
                WHERE f.record_status = 'ACTIVE' AND f.state IS NOT NULL
                GROUP BY 1, 2 ORDER BY count DESC
            " ""))
            recordStatuses = [dict(r._mapping) for r in res]
            
            farmingTypes = [{"code": "ALL", "name": "All"}]
            levels = [{"code": "REGION", "name": "Region"}]
            
            return {
                "regions": regions,
                "recordStatuses": recordStatuses,
                "farmingTypes": farmingTypes,
                "levels": levels
            }
    except Exception as e:
        logger.error(f"Error fetching filter options: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/locations")
async def get_locations(regionId: Optional[str] = None, zoneId: Optional[str] = None, woredaId: Optional[str] = None):
    try:
        async with dbengine.get_engine().connect() as conn:
            if regionId:
                # Get zones for a region
                res = await conn.execute(text("" "
                    SELECT DISTINCT elem->>'level_value_id' AS code, elem->>'level_value_id' AS id, elem->>'level_value_id' AS name
                    FROM g2p_register_farmers f, jsonb_array_elements(f.geo_code_hierarchy_json->'hierarchy') elem
                    WHERE elem->>'level_mnemonic' = 'zone' 
                    AND f.geo_code_hierarchy_json @> jsonb_build_object('hierarchy', jsonb_build_array(jsonb_build_object('level_mnemonic', 'region', 'level_value_id', :parent::text)))
                    AND f.record_status = 'ACTIVE'
                " ""), {"parent": regionId})
                return {"zones": [dict(r._mapping) for r in res]}
            elif zoneId:
                res = await conn.execute(text("" "
                    SELECT DISTINCT elem->>'level_value_id' AS code, elem->>'level_value_id' AS id, elem->>'level_value_id' AS name
                    FROM g2p_register_farmers f, jsonb_array_elements(f.geo_code_hierarchy_json->'hierarchy') elem
                    WHERE elem->>'level_mnemonic' = 'woreda' 
                    AND f.geo_code_hierarchy_json @> jsonb_build_object('hierarchy', jsonb_build_array(jsonb_build_object('level_mnemonic', 'zone', 'level_value_id', :parent::text)))
                    AND f.record_status = 'ACTIVE'
                " ""), {"parent": zoneId})
                return {"woredas": [dict(r._mapping) for r in res]}
            elif woredaId:
                res = await conn.execute(text("" "
                    SELECT DISTINCT elem->>'level_value_id' AS code, elem->>'level_value_id' AS id, elem->>'level_value_id' AS name
                    FROM g2p_register_farmers f, jsonb_array_elements(f.geo_code_hierarchy_json->'hierarchy') elem
                    WHERE elem->>'level_mnemonic' = 'kebele' 
                    AND f.geo_code_hierarchy_json @> jsonb_build_object('hierarchy', jsonb_build_array(jsonb_build_object('level_mnemonic', 'woreda', 'level_value_id', :parent::text)))
                    AND f.record_status = 'ACTIVE'
                " ""), {"parent": woredaId})
                return {"kebeles": [dict(r._mapping) for r in res]}
            else:
                return {}
    except Exception as e:
        logger.error(f"Error fetching locations: {e}")
        raise HTTPException(status_code=500, detail=str(e))
@router.post("/data/export")
async def export_data(payload: dict):
    try:
        filters = payload.get('filters', {})
        region = filters.get('region')
        zone = filters.get('zone')
        woreda = filters.get('woreda')
        kebele = filters.get('kebele')
        record_state = filters.get('recordState', filters.get('state'))
        
        clause, params = build_where_clause(region, zone, woreda, kebele, record_state)
        
        query = f"" "
            SELECT
              f.functional_record_id      AS record_id,
              f.internal_record_id        AS farmer_id,
              f.record_name               AS farmer_name,
              (SELECT elem->>'level_value_name' FROM jsonb_array_elements(f.geo_code_hierarchy_json->'hierarchy') elem WHERE elem->>'level_mnemonic' = 'region' LIMIT 1) AS region,
              (SELECT elem->>'level_value_name' FROM jsonb_array_elements(f.geo_code_hierarchy_json->'hierarchy') elem WHERE elem->>'level_mnemonic' = 'zone' LIMIT 1) AS zone,
              (SELECT elem->>'level_value_name' FROM jsonb_array_elements(f.geo_code_hierarchy_json->'hierarchy') elem WHERE elem->>'level_mnemonic' = 'woreda' LIMIT 1) AS woreda,
              (SELECT elem->>'level_value_name' FROM jsonb_array_elements(f.geo_code_hierarchy_json->'hierarchy') elem WHERE elem->>'level_mnemonic' = 'kebele' LIMIT 1) AS kebele,
              f.state                     AS status,
              c.commodity                 AS commodity,
              f.land_ownership            AS ownership_type,
              c.planted_date              AS sowing_date
            FROM g2p_register_farmers f
            LEFT JOIN g2p_register_crops c
              ON c.link_internal_record_id = f.internal_record_id
             AND c.record_status = 'ACTIVE'
            WHERE f.record_status = 'ACTIVE'
              {clause}
            ORDER BY f.created_at DESC, f.functional_record_id
        " ""
        
        async with dbengine.get_engine().connect() as conn:
            result = await conn.execute(text(query), params)
            rows = [dict(r._mapping) for r in result]
            
            import csv
            import io
            
            if not rows:
                return ""
                
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
            
            from fastapi.responses import PlainTextResponse
            return PlainTextResponse(output.getvalue(), media_type="text/csv")
            
    except Exception as e:
        logger.error(f"Error exporting data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
