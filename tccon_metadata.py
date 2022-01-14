import json
from datacite import schema43

metaf = open("bu_burgos01.json", "r")
metadata = json.load(metaf)

metadata.pop("__last_modified__")
metadata["fundingReferences"] = metadata.pop("FundingReference")
metadata["identifiers"] = [
    {"identifierType": "DOI", "identifier": "https://doi.org/10.1234/example-full"}
]
metadata["publisher"] = "CaltechDATA"
metadata["publicationYear"] = "2022"
metadata["types"] = {"resourceTypeGeneral": "Dataset", "resourceType": "Datset"}
metadata["schemaVersion"] = "http://datacite.org/schema/kernel-4"

valid = schema43.validate(metadata)
if not valid:
    v = schema43.validator.validate(metadata)
    errors = sorted(v.iter_errors(instance), key=lambda e: e.path)
