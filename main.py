@app.post("/api/admin/bulk-import-csv")
async def bulk_import_csv(
    csv_data: dict,
    background_tasks: BackgroundTasks,
    x_admin_token: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Bulk import games from CSV data (admin only)"""
    _require_admin_token(x_admin_token)
    
    try:
        csv_text = csv_data.get("csv_data", "")
        if not csv_text.strip():
            raise HTTPException(status_code=400, detail="No CSV data provided")
        
        lines = [line.strip() for line in csv_text.strip().split('\n') if line.strip()]
        if not lines:
            raise HTTPException(status_code=400, detail="No valid lines in CSV")
        
        added = []
        skipped = []
        errors = []
        
        for line_num, line in enumerate(lines, 1):
            try:
                # Expected format: bgg_id,title (title is optional)
                parts = [p.strip() for p in line.split(',')]
                if len(parts) < 1:
                    errors.append(f"Line {line_num}: No BGG ID provided")
                    continue
                
                # Try to parse BGG ID
                try:
                    bgg_id = int(parts[0])
                except ValueError:
                    errors.append(f"Line {line_num}: Invalid BGG ID '{parts[0]}'")
                    continue
                
                # Check if already exists
                existing = db.execute(select(Game).where(Game.bgg_id == bgg_id)).scalar_one_or_none()
                if existing:
                    skipped.append(f"BGG ID {bgg_id}: Already exists as '{existing.title}'")
                    continue
                
                # Import from BGG
                try:
                    bgg_data = await fetch_bgg_thing(bgg_id)
                    categories_str = ", ".join(bgg_data.get("categories", []))
                    
                    # Create new game
                    categories = _parse_categories(categories_str)
                    game = Game(
                        title=bgg_data["title"],
                        categories=categories_str,
                        year=bgg_data.get("year"),
                        players_min=bgg_data.get("players_min"),
                        players_max=bgg_data.get("players_max"),
                        playtime_min=bgg_data.get("playtime_min"),
                        playtime_max=bgg_data.get("playtime_max"),
                        bgg_id=bgg_id,
                        mana_meeple_category=_categorize_game(categories)
                    )
                    db.add(game)
                    db.commit()
                    db.refresh(game)
                    
                    added.append(f"BGG ID {bgg_id}: {game.title}")
                    
                    # Download thumbnail in background
                    thumbnail_url = bgg_data.get("thumbnail")
                    if thumbnail_url and background_tasks:
                        background_tasks.add_task(_download_and_update_thumbnail, game.id, thumbnail_url)
                    
                except Exception as e:
                    db.rollback()
                    errors.append(f"Line {line_num}: Failed to import BGG ID {bgg_id} - {str(e)}")
                    
            except Exception as e:
                errors.append(f"Line {line_num}: {str(e)}")
        
        return {
            "message": f"Processed {len(lines)} lines",
            "added": added,
            "skipped": skipped,
            "errors": errors
        }
        
    except Exception as e:
        logger.error(f"Bulk import failed: {e}")
        raise HTTPException(status_code=500, detail=f"Bulk import failed: {str(e)}")


@app.post("/api/admin/bulk-categorize-csv")
async def bulk_categorize_csv(
    csv_data: dict,
    x_admin_token: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Bulk categorize existing games from CSV data (admin only)"""
    _require_admin_token(x_admin_token)
    
    try:
        csv_text = csv_data.get("csv_data", "")
        if not csv_text.strip():
            raise HTTPException(status_code=400, detail="No CSV data provided")
        
        lines = [line.strip() for line in csv_text.strip().split('\n') if line.strip()]
        if not lines:
            raise HTTPException(status_code=400, detail="No valid lines in CSV")
        
        updated = []
        not_found = []
        errors = []
        
        for line_num, line in enumerate(lines, 1):
            try:
                # Expected format: bgg_id,category[,title]
                parts = [p.strip() for p in line.split(',')]
                if len(parts) < 2:
                    errors.append(f"Line {line_num}: Must have at least bgg_id,category")
                    continue
                
                # Parse BGG ID
                try:
                    bgg_id = int(parts[0])
                except ValueError:
                    errors.append(f"Line {line_num}: Invalid BGG ID '{parts[0]}'")
                    continue
                
                category = parts[1].strip()
                
                # Validate category (accept both keys and labels)
                category_key = None
                if category in CATEGORY_KEYS:
                    category_key = category
                else:
                    # Try to find by label
                    from constants.categories import CATEGORY_LABELS
                    for key, label in CATEGORY_LABELS.items():
                        if label.lower() == category.lower():
                            category_key = key
                            break
                
                if not category_key:
                    errors.append(f"Line {line_num}: Invalid category '{category}'. Use: {', '.join(CATEGORY_KEYS)}")
                    continue
                
                # Find and update game
                game = db.execute(select(Game).where(Game.bgg_id == bgg_id)).scalar_one_or_none()
                if not game:
                    not_found.append(f"BGG ID {bgg_id}: Game not found")
                    continue
                
                old_category = game.mana_meeple_category
                game.mana_meeple_category = category_key
                db.add(game)
                
                updated.append(f"BGG ID {bgg_id} ({game.title}): {old_category or 'None'} → {category_key}")
                
            except Exception as e:
                errors.append(f"Line {line_num}: {str(e)}")
        
        db.commit()
        
        return {
            "message": f"Processed {len(lines)} lines",
            "updated": updated,
            "not_found": not_found,
            "errors": errors
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Bulk categorize failed: {e}")
        raise HTTPException(status_code=500, detail=f"Bulk categorize failed: {str(e)}")
