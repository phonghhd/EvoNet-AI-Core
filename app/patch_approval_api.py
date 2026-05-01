from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import json

app = FastAPI()

# File paths
DRAFT_FILE = "/app/main_draft.py"
MAIN_FILE = "/app/main.py"
BACKUP_DIR = "/app/logs/backups"

class ApprovalRequest(BaseModel):
    action: str  # "approve" or "reject"

@app.post("/approve-patch")
async def approve_patch(request: ApprovalRequest):
    """API endpoint to approve or reject a patch"""
    if request.action == "approve":
        return await approve_patch_action()
    elif request.action == "reject":
        return await reject_patch_action()
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'approve' or 'reject'.")

async def approve_patch_action():
    """Approve and apply the patch"""
    try:
        if os.path.exists(DRAFT_FILE):
            # Create backup directory if it doesn't exist
            os.makedirs(BACKUP_DIR, exist_ok=True)
            
            # Create backup of current main file
            import time
            backup_name = f"main_backup_{int(time.time())}.py"
            backup_path = os.path.join(BACKUP_DIR, backup_name)
            
            # Copy current main file to backup
            with open(MAIN_FILE, "r") as src, open(backup_path, "w") as dst:
                dst.write(src.read())
            
            # Copy draft file to main file
            with open(DRAFT_FILE, "r") as src, open(MAIN_FILE, "w") as dst:
                dst.write(src.read())
            
            # Remove draft file
            os.remove(DRAFT_FILE)
            
            return {
                "message": "Patch approved and applied successfully",
                "backup": backup_name
            }
        else:
            raise HTTPException(status_code=404, detail="No draft file found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to apply patch: {str(e)}")

async def reject_patch_action():
    """Reject and delete the patch"""
    try:
        if os.path.exists(DRAFT_FILE):
            # Remove draft file
            os.remove(DRAFT_FILE)
            
            return {
                "message": "Patch rejected and deleted successfully"
            }
        else:
            raise HTTPException(status_code=404, detail="No draft file found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reject patch: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)