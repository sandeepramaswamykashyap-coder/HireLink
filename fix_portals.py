
from backend.database import init_db, get_db, PortalStatus
from sqlalchemy.orm import Session

init_db()
db: Session = next(get_db())

# DELETE 'Naukri.com' if 'Naukri' exists
naukri_com = db.query(PortalStatus).filter(PortalStatus.portal_name == "Naukri.com").first()
naukri = db.query(PortalStatus).filter(PortalStatus.portal_name == "Naukri").first()

if naukri_com:
    print(f"Found Naukri.com (ID: {naukri_com.id})")
    if naukri:
        print(f"Also found Naukri (ID: {naukri.id}). Deleting Naukri.com...")
        db.delete(naukri_com)
        db.commit()
        print("Deleted Naukri.com")
    else:
        print("Renaming Naukri.com to Naukri")
        naukri_com.portal_name = "Naukri"
        db.commit()

# List all current
all_s = db.query(PortalStatus).all()
print("Current Portals in DB:")
for s in all_s:
    print(f"- {s.portal_name}")
