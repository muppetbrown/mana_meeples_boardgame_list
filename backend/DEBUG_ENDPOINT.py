# Add this debug endpoint to backend/api/routers/admin.py
# Put it at the bottom of the file, before the last line

@router.get("/debug/bgg-raw/{bgg_id}")
async def debug_bgg_raw_response(
    bgg_id: int,
    _: None = Depends(require_admin_auth)
):
    """
    Debug endpoint to see what BGG XML API actually returns.
    This helps diagnose parsing issues.
    """
    import httpx
    from bgg_service import fetch_bgg_thing, BGGServiceError
    
    result = {
        "bgg_id": bgg_id,
        "timestamp": datetime.now().isoformat(),
    }
    
    # Test 1: Raw HTTP request
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://boardgamegeek.com/xmlapi2/thing",
                params={"id": str(bgg_id), "stats": "1"}
            )
            
            result["http_status"] = response.status_code
            result["http_headers"] = dict(response.headers)
            result["xml_length"] = len(response.text)
            result["xml_preview"] = response.text[:2000]  # First 2000 chars
            result["xml_full"] = response.text  # Full XML (careful with large responses)
            
    except Exception as e:
        result["http_error"] = {
            "type": type(e).__name__,
            "message": str(e)
        }
        return result
    
    # Test 2: Try to parse with our function
    try:
        parsed_data = await fetch_bgg_thing(bgg_id)
        result["parse_success"] = True
        result["parsed_data"] = parsed_data
    except BGGServiceError as e:
        result["parse_success"] = False
        result["parse_error"] = {
            "type": "BGGServiceError",
            "message": str(e)
        }
    except Exception as e:
        result["parse_success"] = False
        result["parse_error"] = {
            "type": type(e).__name__,
            "message": str(e),
            "details": repr(e)
        }
    
    return result
