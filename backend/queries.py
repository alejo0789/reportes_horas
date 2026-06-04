# SQL queries container module

VENTAS_POR_HORA_QUERY = """
WITH params AS (
  SELECT
    TO_DATE(:desde, 'YYYY-MM-DD HH24:MI:SS') AS desde,
    TO_DATE(:hasta, 'YYYY-MM-DD HH24:MI:SS') AS hasta
  FROM dual
),

base_transaccional AS (

  SELECT
    'SIGT_CHANCES' AS src_table,
    t.ide_producto,
    t.ide_sitioventa,
    t.ide_usuario,
    CAST(t.fec_venta AS DATE) AS fec_event,
    NVL(t.vlr_pago_total, 0) AS venta_neta
  FROM GANA_SIGA.SIGT_CHANCES t, params p
  WHERE t.fec_venta >= p.desde
    AND t.fec_venta <  p.hasta
    AND t.ide_estado IN (3)

  UNION ALL

  SELECT
    'SIGT_CHANCES_RASPA' AS src_table,
    22069 AS ide_producto,
    t.ide_sitioventa,
    t.ide_usuario,
    CAST(t.fec_venta AS DATE) AS fec_event,
    NVL(t.vlr_apostado, 0) AS venta_neta
  FROM GANA_SIGA.SIGT_CHANCES_RASPA t, params p
  WHERE t.fec_venta >= p.desde
    AND t.fec_venta <  p.hasta
    AND t.ide_estado IN (3)
    AND NVL(UPPER(TO_CHAR(t.es_premio_otro_tiquete)), 'N') <> 'S'
    AND t.raspa_otro_tiquete IS NULL
  GROUP BY
    CAST(t.fec_venta AS DATE),
    t.ide_sitioventa,
    t.ide_usuario,
    NVL(t.ide_equipo, -1),
    NVL(t.ide_forma_pago_raspa, -1),
    NVL(t.vlr_apostado, 0),
    NVL(t.vlr_nominal_raspa, 0),
    NVL(TO_CHAR(t.raspa), '_NULL_'),
    NVL(TO_CHAR(t.colilla), '_NULL_'),
    NVL(TO_CHAR(t.serie), '_NULL_')

  UNION ALL

  SELECT
    'SIGT_DOBLE_GANA' AS src_table,
    t.ide_producto,
    t.ide_sitioventa,
    t.ide_usuario,
    CAST(t.fec_venta AS DATE) AS fec_event,
    NVL(t.vlr_pago_total, 0) AS venta_neta
  FROM GANA_SIGA.SIGT_DOBLE_GANA t, params p
  WHERE t.fec_venta >= p.desde
    AND t.fec_venta <  p.hasta
    AND t.ide_estado IN (3)

  UNION ALL

  SELECT
    'SIGT_LOTERIAS_LINEA' AS src_table,
    t.ide_producto,
    t.ide_sitioventa,
    t.ide_usuario,
    CAST(t.fec_venta AS DATE) AS fec_event,
    NVL(t.vlr_pagado, 0) AS venta_neta
  FROM GANA_SIGA.SIGT_LOTERIAS_LINEA t, params p
  WHERE t.fec_venta >= p.desde
    AND t.fec_venta <  p.hasta
    AND t.ide_estado IN (3)

  UNION ALL

  SELECT
    'SIGT_RECARGAS' AS src_table,
    t.ide_producto,
    t.ide_sitioventa,
    t.ide_usuario,
    CAST(t.fec_venta AS DATE) AS fec_event,
    NVL(t.vlr_recarga, 0) AS venta_neta
  FROM GANA_SIGA.SIGT_RECARGAS t, params p
  WHERE t.fec_venta >= p.desde
    AND t.fec_venta <  p.hasta
    AND t.ide_estado IN (48)

  UNION ALL

  SELECT
    'SIGT_RECAUDOS_MAESTRO' AS src_table,
    t.ide_producto,
    t.ide_sitioventa,
    t.ide_usuario,
    CAST(t.fec_venta AS DATE) AS fec_event,
    NVL(t.vlr_total_recaudo, 0) AS venta_neta
  FROM GANA_SIGA.SIGT_RECAUDOS_MAESTRO t, params p
  WHERE t.fec_venta >= p.desde
    AND t.fec_venta <  p.hasta
    AND t.ide_estado IN (3)

  UNION ALL

  SELECT
    'SIGT_BALOTO' AS src_table,
    t.ide_producto,
    t.ide_sitioventa,
    t.ide_usuario,
    CAST(t.fec_venta AS DATE) AS fec_event,
    NVL(t.vlr_total_recaudo, 0) AS venta_neta
  FROM GANA_SIGA.SIGT_BALOTO t, params p
  WHERE t.fec_venta >= p.desde
    AND t.fec_venta <  p.hasta
    AND t.ide_estado IN (3)

  UNION ALL

  SELECT
    'SIGT_SUPER_ASTRO' AS src_table,
    t.ide_producto,
    t.ide_sitioventa,
    t.ide_usuario,
    CAST(t.fec_venta AS DATE) AS fec_event,
    NVL(t.vlr_pago_total, 0) AS venta_neta
  FROM GANA_SIGA.SIGT_SUPER_ASTRO t, params p
  WHERE t.fec_venta >= p.desde
    AND t.fec_venta <  p.hasta
    AND t.ide_estado IN (3)

  UNION ALL

  SELECT
    'SIGT_RECAUDOS_EMPRESAS' AS src_table,
    t.ide_producto,
    t.ide_sitioventa,
    t.ide_usuario,
    CAST(t.fec_venta AS DATE) AS fec_event,
    NVL(t.vlr_recaudado, 0) AS venta_neta
  FROM GANA_SIGA.SIGT_RECAUDOS_EMPRESAS t, params p
  WHERE t.fec_venta >= p.desde
    AND t.fec_venta <  p.hasta
    AND t.ide_estado IN (44)

  UNION ALL

  SELECT
    'SIGT_SG_GIROS_CREADOS' AS src_table,
    t.ide_producto,
    t.ide_sitioventa,
    t.ide_usuario,
    CAST(t.fec_giro AS DATE) AS fec_event,
    NVL(t.valor_total, 0) AS venta_neta
  FROM GANA_SIGA.SIGT_SG_GIROS_CREADOS t, params p
  WHERE t.fec_giro >= p.desde
    AND t.fec_giro <  p.hasta
    AND t.ide_producto = 13
    AND t.ide_estado IN (60, 61)
    AND COALESCE(t.ide_estado, -1) NOT IN (63)

  UNION ALL

  SELECT
    'SIGT_SG_GIROS_PAGADOS' AS src_table,
    t.ide_producto,
    t.ide_sitioventa,
    t.ide_usuario,
    CAST(t.fec_pago AS DATE) AS fec_event,
    NVL(t.valor_total, 0) AS venta_neta
  FROM GANA_SIGA.SIGT_SG_GIROS_PAGADOS t, params p
  WHERE t.fec_pago >= p.desde
    AND t.fec_pago <  p.hasta
    AND t.ide_estado IN (61)

  UNION ALL

  SELECT
    'SIGT_PAGOS' AS src_table,
    t.ide_producto,
    t.ide_sitioventa,
    t.ide_usuario,
    CAST(t.fec_pago AS DATE) AS fec_event,
    NVL(t.valor_pago, 0) AS venta_neta
  FROM GANA_SIGA.SIGT_PAGOS t, params p
  WHERE t.fec_pago >= p.desde
    AND t.fec_pago <  p.hasta
    AND t.ide_producto IN (17288, 17900)
    AND t.ide_estado IN (264)

  UNION ALL

  SELECT
    'SIGT_PAGOGEN_MAESTRO' AS src_table,
    t.ide_producto,
    t.ide_sitioventa,
    t.ide_usuario,
    CAST(t.fec_pago AS DATE) AS fec_event,
    NVL(t.vlr_total_pagado, 0) AS venta_neta
  FROM GANA_SIGA.SIGT_PAGOGEN_MAESTRO t, params p
  WHERE t.fec_pago >= p.desde
    AND t.fec_pago <  p.hasta
    AND t.ide_producto IN (21953, 21988, 21991, 21999, 22003, 22010, 22035, 22048, 22066, 22099)
    AND t.ide_estado IN (3)
    AND NOT (
      t.ide_producto = 22066
      AND TO_CHAR(t.fec_pago, 'HH24:MI:SS') = '00:00:00'
    )

  UNION ALL

  SELECT
    'SIGT_VENTA_INCENTIVO_COBRO' AS src_table,
    t.ide_producto,
    t.ide_sitioventa,
    t.ide_usuario,
    CAST(t.fec_venta AS DATE) AS fec_event,
    NVL(t.vlr_pago_total, 0) AS venta_neta
  FROM GANA_SIGA.SIGT_VENTA_INCENTIVO_COBRO t, params p
  WHERE t.fec_venta >= p.desde
    AND t.fec_venta <  p.hasta
    AND t.ide_estado IN (3)
)

SELECT
  ide_sitioventa AS "Cod_Sitio",
  TRUNC(fec_event, 'HH24') AS "Fecha",
  ide_producto AS "Cod_Producto",
  TRUNC(fec_event) AS "Fecha_Dia",
  TO_CHAR(TRUNC(fec_event, 'HH24'), 'HH24:MI:SS') AS "Hora",
  src_table AS "Tabla_Origen",
  SUM(venta_neta) AS "Venta_Neta"
FROM base_transaccional
GROUP BY
  ide_sitioventa,
  TRUNC(fec_event, 'HH24'),
  ide_producto,
  TRUNC(fec_event),
  TO_CHAR(TRUNC(fec_event, 'HH24'), 'HH24:MI:SS'),
  src_table
ORDER BY
  "Fecha",
  "Cod_Sitio",
  "Cod_Producto"
"""

SITIOS_VENTA_QUERY = """
SELECT
    SV.IDE_CIUDAD AS "Cod_Ciudad",
    CIUDAD.NOM_CIUDAD AS "Ciudad",

    OFICINA.IDE_SUBZONA AS "Cod_Subzona",
    SUBZONA.NOM_SUBZONA AS "Subzona",

    SUBZONA.IDE_ZONA AS "Cod_Zona",
    ZONA.NOM_ZONA AS "Zona",

    SV.IDE_OFICINA AS "Cod_Oficina",
    OFICINA.NOM_OFICINA AS "Oficina",

    SV.IDE_SITIOVENTA AS "Cod_Sitio",
    SV.NOM_SITIOVENTA AS "Sitio_Venta",

    SV.IDE_TIPO_SITIO AS "Cod_Tipo_SV",
    TSV.DES_TIPO_SITIO AS "Tipo_SV",

    SV.DIRECCION AS "Direccion",
    SV.ACTIVO AS "Activo",

    SV.FEC_INGRESO AS "Fecha_Ingreso",
    SV.FEC_RETIRO AS "Fecha_Retiro",

    SV.IDE_CATEGORIA AS "Cod_Nivel_SV",

    SV.REG_MERCANTIL AS "Registro_Mercantil",

    SV.CX AS "CX",
    SV.CY AS "CY"

FROM GANA_MAESTROS.MAET_SITIOSVENTA SV

LEFT JOIN GANA_MAESTROS.MAET_CIUDADES CIUDAD
    ON CIUDAD.IDE_CIUDAD = SV.IDE_CIUDAD

LEFT JOIN GANA_MAESTROS.MAET_TIPOS_SITIOVENTA TSV
    ON TSV.IDE_TIPO_SITIO = SV.IDE_TIPO_SITIO

LEFT JOIN GANA_MAESTROS.MAET_OFICINAS OFICINA
    ON OFICINA.IDE_OFICINA = SV.IDE_OFICINA

LEFT JOIN GANA_MAESTROS.MAET_SUBZONAS SUBZONA
    ON SUBZONA.IDE_SUBZONA = OFICINA.IDE_SUBZONA

LEFT JOIN GANA_MAESTROS.MAET_ZONAS ZONA
    ON ZONA.IDE_ZONA = SUBZONA.IDE_ZONA
"""

PRODUCTOS_QUERY = """
SELECT
    SP.IDE_PRODUCTO AS "Cod_Producto",
    SP.DES_PRODUCTO AS "Producto",

    SP.IDE_TIPOPRODUCTO AS "Cod_Tipo_Producto",
    STP.DES_TIPO_PRODUCTO AS "Tipo_Producto",

    SP.ACTIVO AS "Activo",
    SP.ANULAR AS "Permite_Anular",
    SP.IVA_PRODUCTO AS "Iva",
    SP.COMISION AS "Aplica_Comision",
    SP.CONSUME_COLILLA AS "Consume_Colilla",

    SP.FEC_INACTIVACION AS "Fecha_Inactivacion"

FROM GANA_SIGA.SIGT_PRODUCTOS SP

LEFT JOIN GANA_SIGA.SIGT_TIPOS_PRODUCTO STP
    ON STP.IDE_TIPOPRODUCTO = SP.IDE_TIPOPRODUCTO
"""
