"""Hardcoded business/engineer constants shared by every generated document.

This data essentially never changes (one engineer, one license), so it's a
plain module rather than a database table or editable GUI screen. If the
license is renewed or the business address changes, update the values here.
"""

# Same person acts as both "Επιβλέπων" (supervising engineer) and
# "Εγκαταστάτης" (licensed installer) -- kept as separate fields since the
# templates reference each role independently, but they resolve to one name.
SUPERVISOR_NAME = "Κωνσταντίνος Άρμεν"
INSTALLER_NAME = "Κωνσταντίνος Άρμεν"

PROFESSION = "Μηχανολόγος Μηχανικός"
TEE_REGISTRY_NO = "165387"

INSTALLER_SPECIALTY = "Εγκαταστάτης Καύσης"
INSTALLER_REGISTRY_NO = "2584"
INSTALLER_REGISTRY_DATE = "26/09/2024"
INSTALLER_LICENSE_EXPIRY = "31/12/2026"
OVERSIGHT_BODY = "Διεύθυνση Βιομηχανίας Δράμας"

BUSINESS_ADDRESS = "Χρυσοστόμου Σμύρνης, Πετρούσα, 66200 Προσοτσάνη"
BUSINESS_PHONE = "6940842104"


def as_dict() -> dict:
    """Context dict consumed by the document templates as `business.*`."""
    return {
        "supervisor_name": SUPERVISOR_NAME,
        "installer_name": INSTALLER_NAME,
        "profession": PROFESSION,
        "tee_registry_no": TEE_REGISTRY_NO,
        "installer_specialty": INSTALLER_SPECIALTY,
        "installer_registry_no": INSTALLER_REGISTRY_NO,
        "installer_registry_date": INSTALLER_REGISTRY_DATE,
        "installer_license_expiry": INSTALLER_LICENSE_EXPIRY,
        "oversight_body": OVERSIGHT_BODY,
        "business_address": BUSINESS_ADDRESS,
        "business_phone": BUSINESS_PHONE,
    }
