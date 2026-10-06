/**
 * friendlyError.js
 * Normalizador central de errores para NuevaMente.
 * Convierte fallos de red, códigos HTTP y excepciones imprevistas en
 * mensajes pedagógicos claros, comprensibles y libres de tecnicismos agresivos.
 */

export function toFriendlyError(err) {
  if (!err) {
    return {
      status: 500,
      code: 'UNKNOWN_ERROR',
      title: 'Aviso del Sistema',
      message: 'Se produjo un inconveniente temporal. Por favor intenta nuevamente.',
      details: ['No se recibieron detalles adicionales del error.'],
      isNetwork: false,
      actionText: 'Reintentar'
    };
  }

  // Resolver status numérico evitando el bug (err.status || 500 convierte 0 en 500)
  let status = 500;
  if (typeof err.status === 'number') {
    status = err.status;
  } else if (err.name === 'TypeError' || String(err.message || '').toLowerCase().includes('fetch')) {
    status = 0;
  }

  const rawMessage = String(err.message || '');
  const rawCode = String(err.code || '');

  // 1. Fallo de Conexión / Red (Status 0 o TypeError de fetch)
  if (
    status === 0 ||
    rawCode === 'CONNECTION_REFUSED' ||
    rawCode === 'CONNECTION_ERROR' ||
    rawMessage.toLowerCase().includes('fetch') ||
    rawMessage.toLowerCase().includes('network') ||
    rawMessage.toLowerCase().includes('failed to fetch') ||
    rawMessage.toLowerCase().includes('load failed')
  ) {
    return {
      status: 0,
      code: 'CONNECTION_REFUSED',
      title: 'Servidor Fuera de Línea',
      message: 'No fue posible conectar con el servidor backend (FastAPI). Por favor verifica que el servicio esté iniciado.',
      details: [
        'El navegador no pudo comunicarse con la URL configurada.',
        'Verifica que el backend esté ejecutándose en http://localhost:8000.'
      ],
      isNetwork: true,
      actionText: 'Reintentar Conexión'
    };
  }

  // 2. Timeout (408)
  if (status === 408 || rawCode === 'TIMEOUT_ERROR' || rawCode === 'REQUEST_TIMEOUT') {
    return {
      status: 408,
      code: 'REQUEST_TIMEOUT',
      title: 'Tiempo de Espera Agotado',
      message: 'El procesamiento del documento tomó más tiempo del habitual. La tarea puede continuar procesándose en segundo plano.',
      details: [
        'Límite de tiempo de espera alcanzado.',
        'Puedes volver a consultar los formatos en unos instantes con el botón de sincronizar.'
      ],
      isNetwork: false,
      actionText: 'Volver a Consultar'
    };
  }

  // 3. OCI Storage Error (502)
  if (status === 502 || rawCode === 'OCI_STORAGE_ERROR' || rawMessage.includes('OCI') || rawMessage.includes('Storage')) {
    return {
      status: 502,
      code: 'OCI_STORAGE_ERROR',
      title: 'Almacenamiento en Nube No Disponible',
      message: 'El documento fue recibido, pero ocurrió un inconveniente temporal con el servicio de almacenamiento (OCI).',
      details: [
        'El servicio remoto de almacenamiento de objetos no respondió a tiempo.',
        'Puedes volver a intentar la subida en unos momentos.'
      ],
      isNetwork: false,
      actionText: 'Reintentar Subida'
    };
  }

  // 4. Archivo demasiado grande (413)
  if (status === 413 || rawCode === 'FILE_TOO_LARGE') {
    return {
      status: 413,
      code: 'FILE_TOO_LARGE',
      title: 'Archivo Demasiado Grande',
      message: 'El archivo seleccionado supera el límite máximo permitido de 10 MB.',
      details: [
        'Por favor comprime el documento o divídelo antes de subirlo.'
      ],
      isNetwork: false,
      actionText: 'Seleccionar Otro'
    };
  }

  // 5. Formato no soportado (415)
  if (status === 415 || rawCode === 'UNSUPPORTED_MEDIA_TYPE') {
    return {
      status: 415,
      code: 'UNSUPPORTED_MEDIA_TYPE',
      title: 'Formato de Archivo No Admitido',
      message: 'Solo se admiten documentos en formato PDF, Markdown (.md) o Texto (.txt).',
      details: [
        'Por favor selecciona un archivo con extensión .pdf, .md o .txt.'
      ],
      isNetwork: false,
      actionText: 'Elegir Archivo'
    };
  }

  // 6. Archivo vacío / Bad Request (400)
  if (status === 400 || rawCode === 'BAD_REQUEST') {
    return {
      status: 400,
      code: 'BAD_REQUEST',
      title: 'Documento No Válido',
      message: rawMessage && !rawMessage.includes('{') && rawMessage.length < 120
        ? rawMessage
        : 'El documento seleccionado está vacío o no contiene datos legibles para capacitar.',
      details: Array.isArray(err.details) && err.details.length ? err.details : ['Verifica que el archivo no esté dañado ni vacío.'],
      isNetwork: false,
      actionText: 'Verificar Archivo'
    };
  }

  // 7. No encontrado (404)
  if (status === 404 || rawCode === 'DOCUMENT_NOT_FOUND') {
    return {
      status: 404,
      code: 'DOCUMENT_NOT_FOUND',
      title: 'Módulo No Encontrado',
      message: 'El documento solicitado no se encuentra en el repositorio del servidor.',
      details: ['Es posible que haya sido removido o que el identificador no sea válido.'],
      isNetwork: false,
      actionText: 'Ir a Biblioteca'
    };
  }

  // 8. Error de validación (422)
  if (status === 422 || rawCode === 'REQUEST_VALIDATION_ERROR') {
    return {
      status: 422,
      code: 'REQUEST_VALIDATION_ERROR',
      title: 'Parámetros Incompletos',
      message: 'Los parámetros enviados no cumplen con los requerimientos pedagógicos esperados.',
      details: Array.isArray(err.details) && err.details.length ? err.details : [rawMessage],
      isNetwork: false,
      actionText: 'Revisar Datos'
    };
  }

  // 9. Error interno 500 o no catalogado
  const isGenericInternal = status >= 500;
  return {
    status: status,
    code: rawCode || (isGenericInternal ? 'INTERNAL_SERVER_ERROR' : `HTTP_${status}`),
    title: isGenericInternal ? 'Inconveniente Temporal en el Servidor' : `Aviso de Respuesta (${status})`,
    message: rawMessage && rawMessage.length < 120 && !rawMessage.includes('<') && !rawMessage.includes('{')
      ? rawMessage
      : 'Ocurrió un error inesperado al procesar la solicitud en el servidor. Por favor intenta de nuevo en unos momentos.',
    details: Array.isArray(err.details) && err.details.length ? err.details : ['El equipo de desarrollo puede verificar los registros del servidor si el problema continúa.'],
    isNetwork: false,
    actionText: 'Reintentar'
  };
}
