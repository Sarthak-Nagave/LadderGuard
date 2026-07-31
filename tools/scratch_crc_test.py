import sys
sys.path.insert(0, '.')
from services.crc.crc_generator import CRCGenerator
from pathlib import Path

generator = CRCGenerator('CRC32')
test_file = Path('test_crc.txt')
with open(test_file, 'wb') as f:
    f.write(b'test data for CRC checking. This could be any bin file.')

result = generator.generate_from_file(test_file)
print(f'CRC generated: {result.hex_value} in {result.processing_time*1000:.2f}ms')
