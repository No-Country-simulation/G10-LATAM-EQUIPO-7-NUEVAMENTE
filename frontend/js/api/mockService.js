/**
 * mockService.js
 * Generador y simulador de pipeline RAG para modo autónomo / offline.
 * Produce estructuras de datos completas y pedagógicas para CUALQUIER temática.
 */

import { sampleLibrary } from '../data/sampleLibrary.js';

export const mockService = {
  /**
   * Procesa un archivo en modo Mock y retorna el documento estructurado con formato Hackathon
   * @param {Object} fileData { name, size, sampleKey, rawFile }
   * @param {Object} params { perfil, formato, nicho, detalle }
   */
  async processMockPipeline(fileData, params) {
    const targetProfile = params.target_profile || params.perfil || 'intermediate';
    const outputFormat = params.output_format || params.formato || 'all';
    const nicheContext = params.niche_context || params.nicho || 'general';

    // Si es una muestra conocida, clonamos y personalizamos sus parámetros
    if (fileData.sampleKey && sampleLibrary[fileData.sampleKey]) {
      const base = JSON.parse(JSON.stringify(sampleLibrary[fileData.sampleKey]));
      base.metadatos = base.metadatos || {};
      base.metadatos.target_profile = targetProfile;
      base.metadatos.perfil = targetProfile;
      return {
        document: base,
        structuredJson: this.buildOfficialJsonPayload(base, params)
      };
    }

    // Si es un archivo subido arbitrario por el usuario, generamos dinámicamente la estructura pedagógica
    const cleanTitle = fileData.name.replace(/\.[^/.]+$/, "").replace(/[-_]/g, " ");
    const inferredDiscipline = this.inferDiscipline(cleanTitle, nicheContext);

    const generatedDoc = {
      id: `doc_${Date.now()}`,
      filename: fileData.name,
      discipline: inferredDiscipline,
      title: cleanTitle.charAt(0).toUpperCase() + cleanTitle.slice(1),
      description: `Contenido educativo adaptado para perfil [${targetProfile}].`,
      filesize: fileData.size || "1.8 MB",
      metadatos: {
        target_profile: targetProfile,
        tiempo_estudio: "8 min",
        anclaje_rag: 99.3,
        fidelidad: "Alta (99.2% verificada por Agente Revisor)",
        chunks_count: 16
      },
      sections: [
        {
          id: "sec_fundamentos_1",
          title: `Fundamentos y Principios de ${cleanTitle}`,
          summary: `Marco conceptual primario derivado del análisis de fuentes. Expone las premisas esenciales y terminología base requerida para el perfil ${targetProfile}.`,
          key_concepts: ["Concepto Clave A", "Premisa Fundamental", "Metodología", "Validación"],
          flashcards: [
            {
              front: `¿Cuál es el postulado central analizado en ${cleanTitle}?`,
              back: `Establece los principios rectores y la estructura operativa elemental descrita en la sección inicial del documento analizado.`,
              didactic_hint: "Enfócate en la definición primaria y su aplicación práctica directa."
            },
            {
              front: `¿Qué beneficio directo aporta la implementación de estos conceptos?`,
              back: `Permite optimizar los resultados operativos, reducir el margen de error y garantizar el cumplimiento de los estándares de la materia.`,
              didactic_hint: "Piensa en el impacto sobre la calidad, el tiempo y la eficiencia."
            }
          ],
          sintesis: {
            executive_summary: `El documento ${cleanTitle} fundamenta la necesidad de estructurar procesos bajo parámetros rigurosos. Se identifican correlaciones clave entre la teoría de base y su implementación contemporánea.`,
            key_takeaways: [
              "Identificación y definición de los conceptos medulares del tema.",
              "Estandarización de criterios según las mejores prácticas del área.",
              "Enfoque adaptado para maximizar la retención según el perfil seleccionado."
            ],
            key_terms: ["Fundamentos", "Metodología", "Estructura", "Buenas Prácticas"]
          },
          video: {
            title: `Masterclass: Claves Esenciales de ${cleanTitle}`,
            duration: "4:15 min",
            key_points: [
              "Min 0:30 - Introducción y contextualización del tema.",
              "Min 1:50 - Análisis de los conceptos primarios y analogías.",
              "Min 3:20 - Aplicación y resolución de dudas frecuentes."
            ]
          },
          quiz: {
            question: `En relación con ${cleanTitle}, ¿cuál de las siguientes opciones describe mejor su propósito esencial?`,
            options: [
              "Establecer lineamientos coherentes basados en el análisis riguroso de fuentes.",
              "Limitar el acceso a la información únicamente a especialistas del área.",
              "Descartar cualquier método empírico previo sin evaluación previa.",
              "Aislar los procesos del contexto real de aplicación."
            ],
            correct_answer: 0,
            explanation: "El análisis del documento valida que la estructuración rigurosa y fundamentada es el objetivo pedagógico primordial."
          }
        },
        {
          id: "sec_aplicacion_2",
          title: `Aplicaciones Prácticas y Estrategias Avanzadas`,
          summary: `Metodologías de aplicación en situaciones reales, análisis de compensaciones (trade-offs) y criterios de evaluación.`,
          key_concepts: ["Aplicación Práctica", "Estrategia", "Métricas", "Optimización"],
          flashcards: [
            {
              front: `¿Cómo se evalúa la efectividad de las soluciones en este ámbito?`,
              back: `Mediante métricas cuantitativas y cualitativas de rendimiento, coherencia conceptual y alineación con los objetivos estratégicos.`,
              didactic_hint: "Recuerda que lo que no se puede medir difícilmente se puede optimizar."
            }
          ],
          sintesis: {
            executive_summary: `La traslación de la teoría a la práctica exige adaptar los métodos a las particularidades del entorno operativo, gestionando riesgos y priorizando la sostenibilidad del sistema.`,
            key_takeaways: [
              "Medición continua y ajuste iterativo de procesos.",
              "Gestión de riesgos y resolución preventiva de cuellos de botella.",
              "Criterios para escalar la solución de manera segura."
            ],
            key_terms: ["Escalabilidad", "Métricas", "Optimización", "Rendimiento"]
          },
          video: {
            title: `Estrategias de Implementación y Casos Reales`,
            duration: "5:00 min",
            key_points: [
              "Min 0:45 - Errores comunes al implementar estas directivas.",
              "Min 2:15 - Casos de estudio y lecciones aprendidas.",
              "Min 4:00 - Guía paso a paso para la adopción exitosa."
            ]
          },
          quiz: {
            question: `¿Cuál es el factor determinante para el éxito a largo plazo al aplicar estos principios?`,
            options: [
              "La iteración constante con retroalimentación y medición de impacto.",
              "La rigidez absoluta sin admitir adaptaciones al entorno.",
              "Evitar la documentación y el registro de incidencias.",
              "Depender de un único punto de control sin delegación."
            ],
            correct_answer: 0,
            explanation: "La iteración informada por métricas asegura que la estrategia se mantenga relevante y efectiva ante cambios del entorno."
          }
        }
      ]
    };

    return {
      document: generatedDoc,
      structuredJson: this.buildOfficialJsonPayload(generatedDoc, params)
    };
  },

  /**
   * Deduce una disciplina descriptiva para el documento
   */
  inferDiscipline(title, nicho) {
    if (nicho && nicho !== 'general' && nicho !== 'auto') {
      const map = {
        backend: "Ingeniería & Software (Backend)",
        health: "Ciencias Médicas & Salud",
        legal: "Ciencias Jurídicas & Derecho",
        business: "Economía & Negocios",
        humanities: "Humanidades & Educación",
        // Retrocompatibilidad
        frontend: "Desarrollo Web & UX",
        datascience: "Ciencia de Datos",
        ia: "Inteligencia Artificial",
        devops: "Cloud & DevOps"
      };
      if (map[nicho]) return map[nicho];
    }

    const t = title.toLowerCase();
    if (t.includes('c++') || t.includes('python') || t.includes('java') || t.includes('javascript') || t.includes('rust') || t.includes('go') || t.includes('sql') || t.includes('program') || t.includes('software') || t.includes('codigo') || t.includes('algoritmo') || t.includes('red') || t.includes('cloud') || t.includes('backend') || t.includes('frontend')) return "Ingeniería de Software";
    if (t.includes('medicin') || t.includes('salud') || t.includes('neuro') || t.includes('biolog') || t.includes('farmaco') || t.includes('anatom')) return "Ciencias Médicas & Biología";
    if (t.includes('ley') || t.includes('derecho') || t.includes('jurid') || t.includes('normat') || t.includes('penal') || t.includes('civil')) return "Ciencias Jurídicas & Derecho";
    if (t.includes('financ') || t.includes('econom') || t.includes('banc') || t.includes('invers') || t.includes('contab') || t.includes('mercado')) return "Economía & Finanzas";
    if (t.includes('historia') || t.includes('filosof') || t.includes('arte') || t.includes('literatura') || t.includes('sociolog')) return "Humanidades & Ciencias Sociales";
    if (t.includes('fisic') || t.includes('matemat') || t.includes('quimic') || t.includes('calculo')) return "Física & Ciencias Exactas";
    if (t.includes('psicolog') || t.includes('conducta') || t.includes('cognit')) return "Psicología & Neurociencia";

    return "Ciencias Generales";
  },

  /**
   * Construye el JSON estructurado según el contrato v1 acordado (en inglés y filtrado condicional)
   */
  buildOfficialJsonPayload(doc, params) {
    const mainSection = doc.sections[0] || {};
    const targetProfile = params.target_profile || params.perfil || 'intermediate';
    const outputFormat = params.output_format || params.formato || 'all';
    const nicheContext = params.niche_context || params.nicho || 'general';

    const adaptedContent = {
      title: doc.title
    };

    // Si output_format = "flashcards", solo flashcards. Si es quiz, solo quiz; etc. Si es all, los cuatro.
    if (outputFormat === 'all' || outputFormat === 'flashcards') {
      adaptedContent.flashcards = (mainSection.flashcards || []).map(f => ({
        front: f.front || f.frente,
        back: f.back || f.dorso,
        didactic_hint: f.didactic_hint || f.pista_didactica
      }));
    }

    if (outputFormat === 'all' || outputFormat === 'quiz') {
      const q = mainSection.quiz || {};
      adaptedContent.quiz = {
        question: q.question || q.pregunta || "Pregunta de autoevaluación",
        options: q.options || q.opciones || [],
        correct_answer: q.correct_answer !== undefined ? q.correct_answer : (q.correcta !== undefined ? q.correcta : 0),
        explanation: q.explanation || q.explicacion || "Fundamentación conceptual derivada del documento."
      };
    }

    if (outputFormat === 'all' || outputFormat === 'tutorial') {
      const v = mainSection.video || {};
      adaptedContent.tutorial = {
        title: v.title || v.titulo_video || doc.title,
        duration: v.duration || v.duracion || "4:00 min",
        key_points: v.key_points || v.puntos_video || []
      };
    }

    if (outputFormat === 'all' || outputFormat === 'summary') {
      const s = mainSection.sintesis || {};
      adaptedContent.summary = {
        executive_summary: s.executive_summary || s.resumen_ejecutivo || "Síntesis conceptual ejecutiva.",
        key_takeaways: s.key_takeaways || s.puntos_clave || [],
        key_terms: s.key_terms || s.terminos_clave || []
      };
    }

    return {
      status: "completed",
      document_id: doc.id,
      metadata: {
        target_profile: targetProfile,
        output_format: outputFormat,
        niche_context: nicheContext
      },
      quality_evaluation: {
        source_faithfulness: (doc.metadatos?.anclaje_rag || 99.2) / 100,
        pedagogical_coherence: 0.985,
        overall_score: 0.988
      },
      adapted_content: adaptedContent
    };
  }
};
