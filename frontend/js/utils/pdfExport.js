/**
 * pdfExport.js
 * Generador y exportador de documentos PDF ejecutivos para los 4 formatos de NuevaMente:
 * - Síntesis Ejecutiva (TLDR)
 * - Tarjetas de Refuerzo (Flashcards)
 * - Guion Audiovisual Formativo (Video Script)
 * - Evaluación de Competencias (Quiz)
 * 
 * Implementación 100% cliente utilizando jsPDF.
 * Diseñado con tipografía ejecutiva, paginación automática, encabezados y pies de página corporativos.
 */

import { jsPDF } from 'jspdf';
import { notifySuccess, notifyWarning, notifyError } from '../modules/notifications.js';

function safeNotifySuccess(title, msg) {
  try {
    if (typeof window !== 'undefined' && typeof document !== 'undefined') {
      safeNotifySuccess(title, msg);
    }
  } catch {}
}

function safeNotifyWarning(title, msg) {
  try {
    if (typeof window !== 'undefined' && typeof document !== 'undefined') {
      safeNotifyWarning(title, msg);
    }
  } catch {}
}

function safeNotifyError(title, msg) {
  try {
    if (typeof window !== 'undefined' && typeof document !== 'undefined') {
      safeNotifyError(title, msg);
    }
  } catch {}
}

const PAGE_WIDTH = 210;
const PAGE_HEIGHT = 297;
const MARGIN_LEFT = 18;
const MARGIN_RIGHT = 18;
const MARGIN_TOP = 22;
const MARGIN_BOTTOM = 20;
const USABLE_WIDTH = PAGE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT; // 174 mm

/**
 * Sanitiza el título para un nombre de archivo amigable
 */
function sanitizeFileName(title, prefix) {
  const safe = (title || 'documento')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9_-]/g, '_')
    .replace(/_+/g, '_')
    .replace(/^_+|_+$/g, '')
    .substring(0, 36);
  return `${prefix}_${safe || 'capacitacion'}.pdf`;
}

/**
 * Dibuja el encabezado corporativo recurrente en cada página
 */
function drawPageHeader(doc, docTitle, formatName) {
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(10);
  doc.setTextColor(217, 119, 6); // Dorado corporativo
  doc.text('NuevaMente', MARGIN_LEFT, 13);

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(8);
  doc.setTextColor(100, 116, 139); // Gris azulado
  doc.text(' | Capacitación Corporativa con IA', MARGIN_LEFT + 22, 13);

  const metaRight = `${formatName} · ${(docTitle || 'Módulo').substring(0, 42)}`;
  doc.text(metaRight, PAGE_WIDTH - MARGIN_RIGHT, 13, { align: 'right' });

  doc.setDrawColor(226, 232, 240);
  doc.setLineWidth(0.3);
  doc.line(MARGIN_LEFT, 16, PAGE_WIDTH - MARGIN_RIGHT, 16);
}

/**
 * Asegura que haya suficiente espacio vertical para un bloque, creando una nueva página si es necesario
 */
function ensureSpace(doc, neededMm, context) {
  if (context.cursorY + neededMm > PAGE_HEIGHT - MARGIN_BOTTOM) {
    doc.addPage();
    context.cursorY = MARGIN_TOP;
    drawPageHeader(doc, context.docTitle, context.formatName);
  }
}

/**
 * Finaliza el documento numerando las páginas y guardando el archivo
 */
function finalizeAndSave(doc, fileName) {
  const totalPages = doc.getNumberOfPages();
  for (let i = 1; i <= totalPages; i++) {
    doc.setPage(i);

    // Línea separadora del pie
    doc.setDrawColor(226, 232, 240);
    doc.setLineWidth(0.3);
    doc.line(MARGIN_LEFT, PAGE_HEIGHT - 14, PAGE_WIDTH - MARGIN_RIGHT, PAGE_HEIGHT - 14);

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(7.5);
    doc.setTextColor(148, 163, 184);
    doc.text('NuevaMente · Documento de Capacitación Generado con IA', MARGIN_LEFT, PAGE_HEIGHT - 9);
    doc.text(`Página ${i} de ${totalPages}`, PAGE_WIDTH - MARGIN_RIGHT, PAGE_HEIGHT - 9, { align: 'right' });
  }

  if (typeof window !== 'undefined' && typeof doc.save === 'function') {
    doc.save(fileName);
  } else {
    doc.output('arraybuffer');
  }
}

/**
 * Dibuja el banner principal de presentación en la primera página
 */
function drawHeroBanner(doc, context, { badgeText, titleText, metaText }) {
  drawPageHeader(doc, context.docTitle, context.formatName);
  context.cursorY = MARGIN_TOP + 2;

  // Pastilla distintiva del formato
  doc.setFillColor(245, 158, 11);
  doc.roundedRect(MARGIN_LEFT, context.cursorY, 68, 6, 1.5, 1.5, 'F');
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(7.5);
  doc.setTextColor(255, 255, 255);
  doc.text(badgeText.toUpperCase(), MARGIN_LEFT + 4, context.cursorY + 4.2);

  context.cursorY += 10;

  // Título Principal
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(14.5);
  doc.setTextColor(15, 23, 42);
  const titleLines = doc.splitTextToSize(titleText || 'Módulo de Capacitación', USABLE_WIDTH);
  doc.text(titleLines, MARGIN_LEFT, context.cursorY);
  context.cursorY += titleLines.length * 6 + 2;

  // Metadatos complementarios
  if (metaText) {
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(8.5);
    doc.setTextColor(100, 116, 139);
    doc.text(metaText, MARGIN_LEFT, context.cursorY);
    context.cursorY += 5;
  }

  // Divisor dorado decorativo
  doc.setDrawColor(245, 158, 11);
  doc.setLineWidth(0.8);
  doc.line(MARGIN_LEFT, context.cursorY, MARGIN_LEFT + 38, context.cursorY);
  context.cursorY += 8;
}

// ============================================================================
// 1. EXPORTADOR DE SÍNTESIS EJECUTIVA (TLDR)
// ============================================================================

export function exportSummaryPdf(docData, summaryData) {
  try {
    const content = summaryData?.content || summaryData || {};
    const docTitle = docData?.title || docData?.filename || content.title || 'Documento';
    const summaryText = content.summary || content.executive_summary || content.resumen_ejecutivo || '';
    const keyPoints = Array.isArray(content.key_points)
      ? content.key_points
      : (Array.isArray(content.key_takeaways) ? content.key_takeaways : (Array.isArray(content.puntos_clave) ? content.puntos_clave : []));
    const conclusion = content.conclusion || content.conclusion_formativa || null;
    const keyTerms = Array.isArray(content.key_terms) ? content.key_terms : (Array.isArray(content.terminos_clave) ? content.terminos_clave : []);

    if (!summaryText && keyPoints.length === 0) {
      safeNotifyWarning('Formato Vacío', 'No hay información suficiente en la Síntesis Ejecutiva para exportar.');
      return;
    }

    safeNotifySuccess('Generando PDF', 'Preparando la Síntesis Ejecutiva para descarga...');

    const doc = new jsPDF({ format: 'a4', unit: 'mm' });
    const context = {
      docTitle,
      formatName: 'Síntesis Ejecutiva',
      cursorY: MARGIN_TOP
    };

    drawHeroBanner(doc, context, {
      badgeText: 'Síntesis Ejecutiva · TLDR',
      titleText: `Módulo: ${docTitle}`,
      metaText: `Área: ${docData?.area || 'Capacitación General'} · Fecha: ${new Date().toLocaleDateString('es-ES')}`
    });

    // 1. Resumen Ejecutivo
    if (summaryText) {
      ensureSpace(doc, 18, context);
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(11);
      doc.setTextColor(15, 23, 42);
      doc.text('1. Resumen Ejecutivo', MARGIN_LEFT, context.cursorY);
      context.cursorY += 6;

      doc.setFont('helvetica', 'normal');
      doc.setFontSize(9.5);
      doc.setTextColor(51, 65, 85);
      const summaryLines = doc.splitTextToSize(summaryText, USABLE_WIDTH);
      for (const line of summaryLines) {
        ensureSpace(doc, 5.5, context);
        doc.text(line, MARGIN_LEFT, context.cursorY);
        context.cursorY += 5;
      }
      context.cursorY += 4;
    }

    // 2. Puntos Críticos y Procedimientos
    if (keyPoints.length > 0) {
      ensureSpace(doc, 18, context);
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(11);
      doc.setTextColor(15, 23, 42);
      doc.text('2. Puntos Críticos y Procedimientos Operativos', MARGIN_LEFT, context.cursorY);
      context.cursorY += 6;

      doc.setFont('helvetica', 'normal');
      doc.setFontSize(9);
      doc.setTextColor(51, 65, 85);

      keyPoints.forEach((point, idx) => {
        const pointText = typeof point === 'string' ? point : String(point ?? '');
        const lines = doc.splitTextToSize(`${idx + 1}.  ${pointText}`, USABLE_WIDTH);
        ensureSpace(doc, lines.length * 4.8 + 2, context);

        doc.text(lines, MARGIN_LEFT, context.cursorY);
        context.cursorY += lines.length * 4.8 + 2.5;
      });
      context.cursorY += 4;
    }

    // 3. Conclusión y Cierre Formativo
    if (conclusion) {
      ensureSpace(doc, 24, context);
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(11);
      doc.setTextColor(15, 23, 42);
      doc.text('3. Conclusión y Cierre Formativo', MARGIN_LEFT, context.cursorY);
      context.cursorY += 6;

      doc.setFont('helvetica', 'normal');
      doc.setFontSize(9);
      doc.setTextColor(51, 65, 85);
      const conclLines = doc.splitTextToSize(conclusion, USABLE_WIDTH);
      for (const line of conclLines) {
        ensureSpace(doc, 5, context);
        doc.text(line, MARGIN_LEFT, context.cursorY);
        context.cursorY += 4.8;
      }
      context.cursorY += 4;
    }

    // 4. Competencias y Términos Clave
    if (keyTerms.length > 0) {
      ensureSpace(doc, 16, context);
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(10.5);
      doc.setTextColor(15, 23, 42);
      doc.text('4. Competencias y Términos Clave', MARGIN_LEFT, context.cursorY);
      context.cursorY += 5.5;

      doc.setFont('helvetica', 'normal');
      doc.setFontSize(8.5);
      doc.setTextColor(71, 85, 105);
      const termsJoined = keyTerms.map(t => (typeof t === 'string' ? t : String(t ?? ''))).join('  ·  ');
      const termLines = doc.splitTextToSize(termsJoined, USABLE_WIDTH);
      for (const line of termLines) {
        ensureSpace(doc, 5, context);
        doc.text(line, MARGIN_LEFT, context.cursorY);
        context.cursorY += 4.5;
      }
    }

    const fileName = sanitizeFileName(docTitle, 'sintesis_ejecutiva');
    finalizeAndSave(doc, fileName);
  } catch (err) {
    console.error('[pdfExport] Error al exportar Síntesis:', err);
    safeNotifyError('Error de Descarga', 'No fue posible compilar el archivo PDF de la Síntesis.');
  }
}

// ============================================================================
// 2. EXPORTADOR DE TARJETAS DE REFUERZO (FLASHCARDS)
// ============================================================================

export function exportFlashcardsPdf(docData, flashcardsData, cardsList) {
  try {
    const cards = Array.isArray(cardsList) && cardsList.length > 0
      ? cardsList
      : (Array.isArray(flashcardsData?.cards)
          ? flashcardsData.cards
          : (Array.isArray(flashcardsData?.content?.cards)
              ? flashcardsData.content.cards
              : (Array.isArray(flashcardsData) ? flashcardsData : [])));

    if (!cards || cards.length === 0) {
      safeNotifyWarning('Formato Vacío', 'No hay tarjetas de refuerzo disponibles para exportar.');
      return;
    }

    const docTitle = docData?.title || docData?.filename || 'Documento';
    safeNotifySuccess('Generando PDF', `Preparando ${cards.length} tarjetas didácticas para descarga...`);

    const doc = new jsPDF({ format: 'a4', unit: 'mm' });
    const context = {
      docTitle,
      formatName: 'Tarjetas de Refuerzo',
      cursorY: MARGIN_TOP
    };

    drawHeroBanner(doc, context, {
      badgeText: 'Tarjetas de Refuerzo · Memoria Activa',
      titleText: `Módulo: ${docTitle}`,
      metaText: `Total de Tarjetas: ${cards.length} · Fecha: ${new Date().toLocaleDateString('es-ES')}`
    });

    cards.forEach((card, idx) => {
      const frontText = card.front || card.pregunta || card.question || card.concepto || 'Concepto no especificado';
      const backText = card.back || card.respuesta || card.answer || card.explicacion || 'Explicación no especificada';
      const hintText = card.hint || card.pista || null;
      const category = card.category || card.categoria || 'Competencia Clave';

      const frontLines = doc.splitTextToSize(`Concepto / Pregunta: ${frontText}`, USABLE_WIDTH - 8);
      const backLines = doc.splitTextToSize(`Respuesta / Fundamento: ${backText}`, USABLE_WIDTH - 8);
      const hintLines = hintText ? doc.splitTextToSize(`Pista pedagógica: ${hintText}`, USABLE_WIDTH - 8) : [];

      const blockHeight = 12 + frontLines.length * 4.5 + backLines.length * 4.5 + (hintLines.length * 4.5) + 6;

      ensureSpace(doc, blockHeight + 4, context);

      // Marco de la tarjeta
      doc.setDrawColor(203, 213, 225);
      doc.setFillColor(248, 250, 252);
      doc.roundedRect(MARGIN_LEFT, context.cursorY, USABLE_WIDTH, blockHeight, 2, 2, 'FD');

      // Cabecera interna de la tarjeta
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(8);
      doc.setTextColor(217, 119, 6);
      doc.text(`TARJETA ${idx + 1} DE ${cards.length}  ·  ${category.toUpperCase()}`, MARGIN_LEFT + 4, context.cursorY + 6);

      let cardInnerY = context.cursorY + 11;

      // Frente
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(9);
      doc.setTextColor(15, 23, 42);
      doc.text(frontLines, MARGIN_LEFT + 4, cardInnerY);
      cardInnerY += frontLines.length * 4.5 + 2;

      // Reverso
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(8.5);
      doc.setTextColor(51, 65, 85);
      doc.text(backLines, MARGIN_LEFT + 4, cardInnerY);
      cardInnerY += backLines.length * 4.5 + 2;

      // Pista
      if (hintLines.length > 0) {
        doc.setFont('helvetica', 'italic');
        doc.setFontSize(8);
        doc.setTextColor(100, 116, 139);
        doc.text(hintLines, MARGIN_LEFT + 4, cardInnerY);
      }

      context.cursorY += blockHeight + 5;
    });

    const fileName = sanitizeFileName(docTitle, 'tarjetas_refuerzo');
    finalizeAndSave(doc, fileName);
  } catch (err) {
    console.error('[pdfExport] Error al exportar Tarjetas:', err);
    safeNotifyError('Error de Descarga', 'No fue posible compilar el PDF de Tarjetas de Refuerzo.');
  }
}

// ============================================================================
// 3. EXPORTADOR DE GUION FORMATIVO (VIDEO SCRIPT)
// ============================================================================

export function exportVideoGuidePdf(docData, videoData, scenesList) {
  try {
    const scenes = Array.isArray(scenesList) && scenesList.length > 0
      ? scenesList
      : (Array.isArray(videoData?.scenes)
          ? videoData.scenes
          : (Array.isArray(videoData?.content?.scenes)
              ? videoData.content.scenes
              : []));

    if (!scenes || scenes.length === 0) {
      safeNotifyWarning('Formato Vacío', 'No hay escenas disponibles en el Guion Formativo para exportar.');
      return;
    }

    const docTitle = docData?.title || docData?.filename || videoData?.title || 'Documento';
    const duration = videoData?.content?.estimated_duration_minutes || videoData?.estimated_duration_minutes || '4:30';

    safeNotifySuccess('Generando PDF', `Preparando Guion Audiovisual de ${scenes.length} escenas...`);

    const doc = new jsPDF({ format: 'a4', unit: 'mm' });
    const context = {
      docTitle,
      formatName: 'Guion Formativo',
      cursorY: MARGIN_TOP
    };

    drawHeroBanner(doc, context, {
      badgeText: 'Guion Audiovisual Formativo',
      titleText: `Módulo: ${docTitle}`,
      metaText: `Duración Estimada: ${duration} min · Total Escenas: ${scenes.length} · Fecha: ${new Date().toLocaleDateString('es-ES')}`
    });

    scenes.forEach((scene, idx) => {
      const sceneNum = scene.scene_number || idx + 1;
      const title = scene.title || `Escena ${sceneNum}`;
      const secDuration = scene.duration_seconds ? `${scene.duration_seconds} seg` : '30 seg';
      const objective = scene.objective || scene.objetivo || 'Desarrollo pedagógico';
      const visual = scene.visual_description || scene.visuales || 'Presentación en pantalla';
      const narration = scene.narration || scene.locucion || scene.script || 'Sin guion especificado.';

      const objLines = doc.splitTextToSize(`Objetivo Didáctico: ${objective}`, USABLE_WIDTH - 8);
      const visualLines = doc.splitTextToSize(`Enfoque Visual: ${visual}`, USABLE_WIDTH - 8);
      const narrationLines = doc.splitTextToSize(`Locución del Facilitador: "${narration}"`, USABLE_WIDTH - 8);

      const blockHeight = 12 + objLines.length * 4.3 + visualLines.length * 4.3 + narrationLines.length * 4.3 + 6;

      ensureSpace(doc, blockHeight + 4, context);

      // Marco de la escena
      doc.setDrawColor(203, 213, 225);
      doc.setFillColor(248, 250, 252);
      doc.roundedRect(MARGIN_LEFT, context.cursorY, USABLE_WIDTH, blockHeight, 2, 2, 'FD');

      // Título de la escena
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(9);
      doc.setTextColor(15, 23, 42);
      doc.text(`ESCENA ${sceneNum}: ${title.toUpperCase()}  (${secDuration})`, MARGIN_LEFT + 4, context.cursorY + 6);

      let innerY = context.cursorY + 11;

      // Objetivo
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(8);
      doc.setTextColor(71, 85, 105);
      doc.text(objLines, MARGIN_LEFT + 4, innerY);
      innerY += objLines.length * 4.3 + 1.5;

      // Visual
      doc.text(visualLines, MARGIN_LEFT + 4, innerY);
      innerY += visualLines.length * 4.3 + 1.5;

      // Locución
      doc.setFont('helvetica', 'italic');
      doc.setTextColor(15, 23, 42);
      doc.text(narrationLines, MARGIN_LEFT + 4, innerY);

      context.cursorY += blockHeight + 5;
    });

    const fileName = sanitizeFileName(docTitle, 'guion_formativo');
    finalizeAndSave(doc, fileName);
  } catch (err) {
    console.error('[pdfExport] Error al exportar Guion:', err);
    safeNotifyError('Error de Descarga', 'No fue posible compilar el PDF del Guion Formativo.');
  }
}

// ============================================================================
// 4. EXPORTADOR DE EVALUACIÓN (QUIZ)
// ============================================================================

export function exportQuizPdf(docData, quizData, questionsList) {
  try {
    const questions = Array.isArray(questionsList) && questionsList.length > 0
      ? questionsList
      : (Array.isArray(quizData?.questions)
          ? quizData.questions
          : (Array.isArray(quizData?.content?.questions)
              ? quizData.content.questions
              : (Array.isArray(quizData) ? quizData : [])));

    if (!questions || questions.length === 0) {
      safeNotifyWarning('Formato Vacío', 'No hay preguntas disponibles en la Evaluación para exportar.');
      return;
    }

    const docTitle = docData?.title || docData?.filename || 'Documento';
    safeNotifySuccess('Generando PDF', `Preparando Evaluación de ${questions.length} preguntas con justificaciones...`);

    const doc = new jsPDF({ format: 'a4', unit: 'mm' });
    const context = {
      docTitle,
      formatName: 'Evaluación (Quiz)',
      cursorY: MARGIN_TOP
    };

    drawHeroBanner(doc, context, {
      badgeText: 'Evaluación de Competencias · Quiz',
      titleText: `Módulo: ${docTitle}`,
      metaText: `Total de Preguntas: ${questions.length} · Fecha: ${new Date().toLocaleDateString('es-ES')}`
    });

    questions.forEach((q, idx) => {
      const qText = q.question || q.pregunta || `Pregunta ${idx + 1}`;
      const options = Array.isArray(q.options) ? q.options : (Array.isArray(q.opciones) ? q.opciones : []);
      const correctAns = q.correct_answer || q.respuesta_correcta || '';
      const explanation = q.explanation || q.explicacion || q.justificacion || '';

      const qLines = doc.splitTextToSize(`${idx + 1}.  ${qText}`, USABLE_WIDTH);
      let optionsTotalLines = 0;
      const formattedOptions = options.map((opt, oIdx) => {
        const letter = String.fromCharCode(65 + oIdx);
        const optText = typeof opt === 'string' ? opt : (opt?.text || String(opt ?? ''));
        const optLines = doc.splitTextToSize(`   [  ]  ${letter})  ${optText}`, USABLE_WIDTH - 6);
        optionsTotalLines += optLines.length;
        return optLines;
      });

      const explLines = explanation ? doc.splitTextToSize(`Justificación pedagógica: ${explanation}`, USABLE_WIDTH - 8) : [];
      const correctLines = correctAns ? doc.splitTextToSize(`✓ Respuesta Correcta: ${correctAns}`, USABLE_WIDTH - 8) : [];

      const neededSpace = qLines.length * 4.8 + optionsTotalLines * 4.5 + (correctLines.length + explLines.length) * 4.2 + 14;
      ensureSpace(doc, neededSpace, context);

      // Pregunta
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(9.5);
      doc.setTextColor(15, 23, 42);
      doc.text(qLines, MARGIN_LEFT, context.cursorY);
      context.cursorY += qLines.length * 4.8 + 2;

      // Opciones
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(8.5);
      doc.setTextColor(51, 65, 85);
      formattedOptions.forEach(optLines => {
        doc.text(optLines, MARGIN_LEFT + 2, context.cursorY);
        context.cursorY += optLines.length * 4.5;
      });
      context.cursorY += 2;

      // Caja de clave de respuesta y justificación
      if (correctAns || explanation) {
        const boxHeight = (correctLines.length + explLines.length) * 4.2 + 5;
        doc.setDrawColor(203, 213, 225);
        doc.setFillColor(241, 245, 249);
        doc.roundedRect(MARGIN_LEFT + 2, context.cursorY, USABLE_WIDTH - 4, boxHeight, 1.5, 1.5, 'FD');

        let ansY = context.cursorY + 4.5;
        if (correctLines.length > 0) {
          doc.setFont('helvetica', 'bold');
          doc.setFontSize(8);
          doc.setTextColor(4, 120, 87); // Verde #047857
          doc.text(correctLines, MARGIN_LEFT + 6, ansY);
          ansY += correctLines.length * 4.2;
        }

        if (explLines.length > 0) {
          doc.setFont('helvetica', 'normal');
          doc.setFontSize(7.5);
          doc.setTextColor(71, 85, 105);
          doc.text(explLines, MARGIN_LEFT + 6, ansY);
        }

        context.cursorY += boxHeight + 6;
      } else {
        context.cursorY += 4;
      }
    });

    const fileName = sanitizeFileName(docTitle, 'evaluacion_quiz');
    finalizeAndSave(doc, fileName);
  } catch (err) {
    console.error('[pdfExport] Error al exportar Quiz:', err);
    safeNotifyError('Error de Descarga', 'No fue posible compilar el PDF de la Evaluación.');
  }
}
