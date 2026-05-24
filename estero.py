"""
estereo.py

Autor: Xavi Prats Castillo

Módulo para el manejo de señales de audio estéreo en formato WAVE (PCM lineal de 16 bits).
Funciones: estereo2mono, mono2estereo, codEstereo, decEstereo.
Solo se utiliza el módulo struct.
"""

import struct


def _lee_cabecera(f):
    riff, tamanyo_riff, wave = struct.unpack('<4sI4s', f.read(12))
    if riff != b'RIFF' or wave != b'WAVE':
        raise ValueError("El fichero no es un fichero WAVE válido.")

    fmt_id, tamanyo_fmt = struct.unpack('<4sI', f.read(8))
    if fmt_id != b'fmt ':
        raise ValueError("No se encontró el subcacho 'fmt '.")

    fmt_data = f.read(tamanyo_fmt)
    audio_format, num_channels, sample_rate, byte_rate, block_align, bits_per_sample = \
        struct.unpack('<HHIIHH', fmt_data[:16])

    if audio_format != 1:
        raise ValueError("Solo se admite PCM lineal (audio_format == 1).")

    data_id, tamanyo_data = struct.unpack('<4sI', f.read(8))
    if data_id != b'data':
        raise ValueError("No se encontró el subcacho 'data'.")

    return {
        'audio_format': audio_format,
        'num_channels': num_channels,
        'sample_rate': sample_rate,
        'byte_rate': byte_rate,
        'block_align': block_align,
        'bits_per_sample': bits_per_sample,
        'tamanyo_data': tamanyo_data,
    }


def _escribe_cabecera(f, num_channels, sample_rate, bits_per_sample, tamanyo_data):
    block_align = num_channels * bits_per_sample // 8
    byte_rate = sample_rate * block_align
    tamanyo_riff = 4 + 8 + 16 + 8 + tamanyo_data

    f.write(struct.pack('<4sI4s', b'RIFF', tamanyo_riff, b'WAVE'))
    f.write(struct.pack('<4sI', b'fmt ', 16))
    f.write(struct.pack('<HHIIHH', 1, num_channels, sample_rate,
                        byte_rate, block_align, bits_per_sample))
    f.write(struct.pack('<4sI', b'data', tamanyo_data))


def estereo2mono(ficEste, ficMono, canal=2):
    if canal not in (0, 1, 2, 3):
        raise ValueError("canal debe ser 0, 1, 2 o 3.")

    with open(ficEste, 'rb') as fe:
        cab = _lee_cabecera(fe)
        if cab['num_channels'] != 2:
            raise ValueError("El fichero de entrada no es estéreo.")
        if cab['bits_per_sample'] != 16:
            raise ValueError("Solo se admiten señales de 16 bits.")

        num_muestras = cab['tamanyo_data'] // cab['block_align']
        muestras = struct.unpack(f'<{num_muestras * 2}h', fe.read(cab['tamanyo_data']))

    izq = muestras[0::2]
    der = muestras[1::2]

    if canal == 0:
        mono = izq
    elif canal == 1:
        mono = der
    elif canal == 2:
        mono = tuple((l + r) // 2 for l, r in zip(izq, der))
    else:
        mono = tuple((l - r) // 2 for l, r in zip(izq, der))

    tamanyo_data = len(mono) * 2
    with open(ficMono, 'wb') as fm:
        _escribe_cabecera(fm, 1, cab['sample_rate'], 16, tamanyo_data)
        fm.write(struct.pack(f'<{len(mono)}h', *mono))


def mono2estereo(ficIzq, ficDer, ficEste):
    with open(ficIzq, 'rb') as fi:
        cab_i = _lee_cabecera(fi)
        if cab_i['num_channels'] != 1:
            raise ValueError("ficIzq no es mono.")
        if cab_i['bits_per_sample'] != 16:
            raise ValueError("Solo se admiten señales de 16 bits.")
        n_i = cab_i['tamanyo_data'] // 2
        izq = struct.unpack(f'<{n_i}h', fi.read(cab_i['tamanyo_data']))

    with open(ficDer, 'rb') as fd:
        cab_d = _lee_cabecera(fd)
        if cab_d['num_channels'] != 1:
            raise ValueError("ficDer no es mono.")
        if cab_d['bits_per_sample'] != 16:
            raise ValueError("Solo se admiten señales de 16 bits.")
        n_d = cab_d['tamanyo_data'] // 2
        der = struct.unpack(f'<{n_d}h', fd.read(cab_d['tamanyo_data']))

    if cab_i['sample_rate'] != cab_d['sample_rate']:
        raise ValueError("Los ficheros no tienen la misma frecuencia de muestreo.")
    if n_i != n_d:
        raise ValueError("Los ficheros no tienen el mismo número de muestras.")

    intercalado = [val for par in zip(izq, der) for val in par]
    tamanyo_data = len(intercalado) * 2

    with open(ficEste, 'wb') as fe:
        _escribe_cabecera(fe, 2, cab_i['sample_rate'], 16, tamanyo_data)
        fe.write(struct.pack(f'<{len(intercalado)}h', *intercalado))


def codEstereo(ficEste, ficCod):
    with open(ficEste, 'rb') as fe:
        cab = _lee_cabecera(fe)
        if cab['num_channels'] != 2:
            raise ValueError("El fichero de entrada no es estéreo.")
        if cab['bits_per_sample'] != 16:
            raise ValueError("Solo se admiten señales de 16 bits.")

        num_muestras = cab['tamanyo_data'] // cab['block_align']
        muestras = struct.unpack(f'<{num_muestras * 2}h', fe.read(cab['tamanyo_data']))

    izq = muestras[0::2]
    der = muestras[1::2]

    codificadas = [
        (((l + r) // 2) << 16) | (((l - r) // 2) & 0xFFFF)
        for l, r in zip(izq, der)
    ]

    tamanyo_data = len(codificadas) * 4
    with open(ficCod, 'wb') as fc:
        _escribe_cabecera(fc, 1, cab['sample_rate'], 32, tamanyo_data)
        fc.write(struct.pack(f'<{len(codificadas)}i', *codificadas))


def decEstereo(ficCod, ficEste):
    with open(ficCod, 'rb') as fc:
        cab = _lee_cabecera(fc)
        if cab['num_channels'] != 1:
            raise ValueError("El fichero codificado debe ser mono.")
        if cab['bits_per_sample'] != 32:
            raise ValueError("El fichero codificado debe tener 32 bits por muestra.")

        num_muestras = cab['tamanyo_data'] // 4
        codificadas = struct.unpack(f'<{num_muestras}i', fc.read(cab['tamanyo_data']))

    semisumas = [v >> 16 for v in codificadas]
    semidifs = [
        (v & 0xFFFF) if (v & 0x8000) == 0 else (v & 0xFFFF) - 0x10000
        for v in codificadas
    ]

    intercalado = [val for s, d in zip(semisumas, semidifs) for val in (s + d, s - d)]

    tamanyo_data = len(intercalado) * 2
    with open(ficEste, 'wb') as fe:
        _escribe_cabecera(fe, 2, cab['sample_rate'], 16, tamanyo_data)
        fe.write(struct.pack(f'<{len(intercalado)}h', *intercalado))