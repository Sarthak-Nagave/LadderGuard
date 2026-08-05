from pathlib import Path

from services.signature_reader import SignatureReaderService

root = Path(r'C:/Users/SM 464/Desktop/8.18.5 Operational Method')

for folder_name in ['3. Operational Flow', '4. Test Report', '5. Automation Input Doc', '6. Ladder Flow']:
    folder = root / folder_name
    print('FOLDER', folder_name, 'exists', folder.exists())
    if not folder.exists():
        continue
    pdfs = sorted([p for p in folder.rglob('*.pdf') if p.is_file()])
    print('PDFS', [p.name for p in pdfs])
    signed = [p for p in pdfs if '-sgn' in p.stem.lower()]
    print('SIGNED', [p.name for p in signed])
    for pdf in signed:
        print('READ', pdf)
        try:
            sigs = SignatureReaderService.read(pdf)
            print('COUNT', len(sigs))
            for s in sigs:
                print('SIGNER', s.signer_name, 'name_found=', s.name_found, 'signature_found=', s.signature_found, 'signed_at=', s.signed_at, 'certificate=', s.certificate)
        except Exception as exc:
            print('ERROR', type(exc).__name__, exc)
    print('---')
