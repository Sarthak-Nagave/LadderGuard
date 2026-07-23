from pathlib import Path
from validators.document_validator import DocumentValidator
from core.validation_context import ValidationContext
from core.validation_step import ValidationStep
from models.signature_info import SignatureInfo
from config import REQUIRED_SIGNERS

class FakeSearch:
    def recursive_files(self, directory, extension):
        return [Path('doc-sgn.pdf')]

class FakeReader:
    def read(self, path):
        return 'plain document text'

class FakeSignatureReader:
    def read(self, path):
        return [SignatureInfo(signer_name=s, name_found=True, signature_found=True) for s in REQUIRED_SIGNERS]

dv = DocumentValidator(ValidationStep.OPERATIONAL_FLOW, '3. Operational Flow', FakeSearch(), FakeReader(), FakeSignatureReader())
ctx = ValidationContext(project_path=Path('.'))
ctx.add_folder('3. Operational Flow', Path('.'))
result = dv.validate(ctx)
print(result.status.name)
print(result.reason)
print([s.to_dict() for s in result.details['signers']])
