/**
 * friendlyError.js
 * Normalizador central de errores para NuevaMente.
 * Convierte fallos de red, códigos HTTP y excepciones imprevistas en
 * mensajes pedagógicos claros, comprensibles y libres de tecnicismos agresivos.
 */

import { CONFIG } from '../config.js';

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

  const rawCode = String(err.code || err.rawBody?.code || '');
  const rawMessage = String(err.message || err.rawBody?.detail || err.rawBody?.message || '');

  // 1. Errores de transporte y red del cliente (prioritarios)
  if (
    rawCode === 'CONNECTION_REFUSED' ||
    rawCode === 'CONNECTION_ERROR' ||
    status === 0 ||
    err.name === 'TypeError' ||
    rawMessage.toLowerCase().includes('fetch') ||
    rawMessage.toLowerCase().includes('network') ||
    rawMessage.toLowerCase().includes('failed to fetch') ||
    rawMessage.toLowerCase().includes('load failed')
  ) {
    return {
      status: 0,
      code: 'CONNECTION_REFUSED',
      title: 'Servidor Fuera de Línea',
      message: 'No fue posible conectar con el servidor backend. Por favor verifica que el servicio esté iniciado y accesible.',
      details: [
        'El navegador no pudo comunicarse con la URL configurada.',
        `Verifica que el servicio backend esté activo en ${CONFIG.API.DEFAULT_BASE_URL}.`
      ],
      isNetwork: true,
      actionText: 'Reintentar Conexión'
    };
  }

  if (rawCode === 'REQUEST_TIMEOUT' || rawCode === 'TIMEOUT_ERROR' || status === 408) {
    return {
      status: 408,
      code: 'REQUEST_TIMEOUT',
      title: 'Tiempo de Espera Agotado',
      message: 'El procesamiento de la solicitud tomó más tiempo del habitual. La tarea puede continuar procesándose en segundo plano.',
      details: [
        'Límite de tiempo de espera alcanzado en el cliente.',
        'Puedes volver a consultar los formatos en unos instantes con el botón de sincronizar.'
      ],
      isNetwork: false,
      actionText: 'Volver a Consultar'
    };
  }

  if (rawCode === 'API_CONTRACT_ERROR') {
    return {
      status: status || 200,
      code: 'API_CONTRACT_ERROR',
      title: 'Discrepancia en Respuesta del Servidor',
      message: rawMessage || 'La respuesta recibida del servidor no cumple con el contrato de datos esperado.',
      details: Array.isArray(err.details) && err.details.length ? err.details : ['El esquema de respuesta no contiene las propiedades esperadas por la aplicación.'],
      isNetwork: false,
      actionText: 'Reintentar'
    };
  }

  // 2. Mapeo funcional por CODE de Backend (Auditoria.md Sec 11)
  if (rawCode === 'FORMAT_REGENERATION_IN_PROGRESS') {
    return {
      status: 409,
      code: 'FORMAT_REGENERATION_IN_PROGRESS',
      title: 'Regeneración en Proceso',
      message: 'Ya existe un intento de generación activo en segundo plano para los formatos solicitados.',
      details: ['El servidor continúa procesando la solicitud previa. Se mantendrá el sondeo reactivo.'],
      isNetwork: false,
      actionText: 'Continuar Espera'
    };
  }

  if (rawCode === 'DOCUMENT_NOT_INDEXED') {
    return {
      status: 409,
      code: 'DOCUMENT_NOT_INDEXED',
      title: 'Documento No Preparado',
      message: 'El documento debe completar la indexación antes de poder regenerar sus formatos formativos.',
      details: ['Espera a que finalice el proceso de indexación inicial antes de reintentar.'],
      isNetwork: false,
      actionText: 'Esperar Indexación'
    };
  }

  if (rawCode === 'FORMAT_CONTEXT_NOT_FOUND') {
    return {
      status: 409,
      code: 'FORMAT_CONTEXT_NOT_FOUND',
      title: 'Contexto Pedagógico No Encontrado',
      message: 'No existe un registro de generación previo para regenerar este formato en el documento.',
      details: ['Intenta cargar el recurso nuevamente o solicitar la generación inicial.'],
      isNetwork: false,
      actionText: 'Volver al Catálogo'
    };
  }

  if (rawCode === 'FORMAT_CONTEXT_CONFLICT') {
    return {
      status: 409,
      code: 'FORMAT_CONTEXT_CONFLICT',
      title: 'Conflicto de Contexto Pedagógico',
      message: 'Los formatos solicitados tienen contextos incompatibles. Intenta regenerarlos de forma individual.',
      details: ['Solicita la regeneración por separado para cada pestaña.'],
      isNetwork: false,
      actionText: 'Reintentar por Separado'
    };
  }

  if (rawCode === 'DOCUMENT_STATE_CONFLICT') {
    return {
      status: 409,
      code: 'DOCUMENT_STATE_CONFLICT',
      title: 'Conflicto de Estado en el Documento',
      message: rawMessage || 'El documento se encuentra en un estado incompatible con la operación solicitada.',
      details: ['El estado actual del documento no admite esta acción.'],
      isNetwork: false,
      actionText: 'Revisar Recurso'
    };
  }

  if (rawCode === 'RAG_INDEXING_FAILED') {
    return {
      status: 502,
      code: 'RAG_INDEXING_FAILED',
      title: 'Fallo en Indexación RAG',
      message: 'No fue posible completar la indexación y análisis del documento con el motor RAG.',
      details: Array.isArray(err.details) && err.details.length ? err.details : ['El servicio RAG no pudo vectorizar o segmentar el documento corporativo.'],
      isNetwork: false,
      actionText: 'Reintentar Subida'
    };
  }

  if (rawCode === 'DOCUMENT_STORAGE_FAILED' || rawCode === 'OCI_STORAGE_ERROR') {
    return {
      status: 502,
      code: rawCode,
      title: 'Almacenamiento en Nube No Disponible',
      message: 'Ocurrió un inconveniente temporal con el servicio de almacenamiento de objetos (OCI).',
      details: ['El bucket remoto de almacenamiento no respondió a tiempo. Puedes volver a intentar en unos momentos.'],
      isNetwork: false,
      actionText: 'Reintentar Subida'
    };
  }

  if (rawCode === 'DOCUMENT_RETRIEVAL_FAILED') {
    return {
      status: 502,
      code: 'DOCUMENT_RETRIEVAL_FAILED',
      title: 'Recuperación de Archivo No Disponible',
      message: 'No fue posible recuperar el archivo original desde el servicio de almacenamiento.',
      details: ['El objeto en la nube no se encuentra disponible temporalmente.'],
      isNetwork: false,
      actionText: 'Reintentar'
    };
  }

  if (rawCode === 'FORMAT_REGISTRATION_FAILED' || rawCode === 'FORMAT_REGENERATION_REGISTRATION_FAILED') {
    return {
      status: 500,
      code: rawCode,
      title: 'Fallo al Registrar Formatos',
      message: 'El documento fue procesado pero no fue posible registrar el nuevo intento de formatos.',
      details: ['Ocurrió un fallo en la persistencia del intento de generación.'],
      isNetwork: false,
      actionText: 'Reintentar'
    };
  }

  if (rawCode === 'FILE_TOO_LARGE' || status === 413) {
    return {
      status: 413,
      code: 'FILE_TOO_LARGE',
      title: 'Archivo Demasiado Grande',
      message: 'El archivo seleccionado supera el límite máximo permitido de 10 MB.',
      details: ['Por favor comprime el documento o divídelo antes de subirlo.'],
      isNetwork: false,
      actionText: 'Seleccionar Otro'
    };
  }

  if (rawCode === 'UNSUPPORTED_MEDIA_TYPE' || rawCode === 'UNSUPPORTED_FILE_TYPE' || rawCode === 'MIME_TYPE_MISMATCH' || status === 415) {
    return {
      status: 415,
      code: rawCode || 'UNSUPPORTED_MEDIA_TYPE',
      title: 'Formato de Archivo No Admitido',
      message: 'Solo se admiten documentos en formato PDF, Markdown (.md) o Texto plano (.txt).',
      details: ['Por favor selecciona un archivo con extensión .pdf, .md o .txt.'],
      isNetwork: false,
      actionText: 'Elegir Archivo'
    };
  }

  if (rawCode === 'DOCUMENT_NOT_FOUND' || status === 404) {
    return {
      status: 404,
      code: 'DOCUMENT_NOT_FOUND',
      title: 'Recurso No Encontrado',
      message: 'El documento solicitado no se encuentra en el repositorio del servidor.',
      details: ['Es posible que haya sido removido o que el identificador no sea válido.'],
      isNetwork: false,
      actionText: 'Ir al Catálogo'
    };
  }

  if (rawCode === 'DOCUMENT_EMPTY' || rawCode === 'DOCUMENT_FILENAME_REQUIRED' || rawCode === 'BAD_REQUEST' || status === 400) {
    return {
      status: 400,
      code: rawCode || 'BAD_REQUEST',
      title: 'Documento No Válido',
      message: rawMessage && !rawMessage.includes('{') && rawMessage.length < 120
        ? rawMessage
        : 'El documento seleccionado está vacío o no contiene datos legibles para capacitar.',
      details: Array.isArray(err.details) && err.details.length ? err.details : ['Verifica que el archivo contenga texto y no esté dañado.'],
      isNetwork: false,
      actionText: 'Verificar Archivo'
    };
  }

  if (rawCode === 'REQUEST_VALIDATION_ERROR' || status === 422) {
    const errorDetails = Array.isArray(err.errors) && err.errors.length
      ? err.errors.map(e => `${e.field ? `${e.field}: ` : ''}${e.message || e.msg || ''}`)
      : (Array.isArray(err.details) && err.details.length ? err.details : [rawMessage || 'Parámetros no válidos.']);
    return {
      status: 422,
      code: 'REQUEST_VALIDATION_ERROR',
      title: 'Parámetros Incompletos o Inválidos',
      message: 'Los parámetros enviados no cumplen con los requerimientos esperados.',
      details: errorDetails,
      isNetwork: false,
      actionText: 'Revisar Datos'
    };
  }

  if (status === 409) {
    return {
      status: 409,
      code: rawCode || 'CONFLICT',
      title: 'Conflicto de Estado',
      message: rawMessage || 'La operación solicitada no es válida en el estado actual del documento o formato.',
      details: Array.isArray(err.details) && err.details.length ? err.details : ['Verifica el estado actual del recurso.'],
      isNetwork: false,
      actionText: 'Reintentar'
    };
  }

  // 3. Fallbacks por HTTP status
  if (status === 502) {
    return {
      status: 502,
      code: rawCode || 'BAD_GATEWAY',
      title: 'Servicio Externo No Disponible',
      message: rawMessage && !rawMessage.includes('{') && rawMessage.length < 120
        ? rawMessage
        : 'Una dependencia externa o servicio de integración no respondió a tiempo.',
      details: Array.isArray(err.details) && err.details.length ? err.details : ['Puedes reintentar en unos momentos mientras el servicio se estabiliza.'],
      isNetwork: false,
      actionText: 'Reintentar'
    };
  }

  // 4. Error interno 500 o no catalogado
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
