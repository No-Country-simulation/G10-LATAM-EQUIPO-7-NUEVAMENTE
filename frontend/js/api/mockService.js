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
    // Si es una muestra conocida, clonamos y personalizamos sus parámetros
    if (fileData.sampleKey && sampleLibrary[fileData.sampleKey]) {
      const base = JSON.parse(JSON.stringify(sampleLibrary[fileData.sampleKey]));
      base.metadatos.perfil = params.perfil;
      base.metadatos.nivel_detalle = params.detalle;
      return {
        document: base,
        structuredJson: this.buildOfficialJsonPayload(base, params)
      };
    }

    // Si es un archivo subido arbitrario por el usuario, generamos dinámicamente la estructura pedagógica
    const cleanTitle = fileData.name.replace(/\.[^/.]+$/, "").replace(/[-_]/g, " ");
    const inferredDiscipline = this.inferDiscipline(cleanTitle, params.nicho);

    const generatedDoc = {
      id: `doc_${Date.now()}`,
      filename: fileData.name,
      discipline: inferredDiscipline,
      title: cleanTitle.charAt(0).toUpperCase() + cleanTitle.slice(1),
      description: `Contenido educativo adaptado para perfil [${params.perfil}] con nivel [${params.detalle}].`,
      filesize: fileData.size || "1.8 MB",
      metadatos: {
        perfil: params.perfil,
        nivel_detalle: params.detalle,
        tiempo_estudio: "8 min",
        anclaje_rag: 99.3,
        fidelidad: "Alta (99.2% verificada por Agente Revisor)",
        chunks_count: 16
      },
      sections: [
        {
          id: "sec_fundamentos_1",
          title: `Fundamentos y Principios de ${cleanTitle}`,
          summary: `Marco conceptual primario derivado del análisis de fuentes. Expone las premisas esenciales y terminología base requerida para el perfil ${params.perfil}.`,
          key_concepts: ["Concepto Clave A", "Premisa Fundamental", "Metodología", "Validación"],
          flashcards: [
            {
              frente: `¿Cuál es el postulado central analizado en ${cleanTitle}?`,
              dorso: `Establece los principios rectores y la estructura operativa elemental descrita en la sección inicial del documento analizado.`,
              pista_didactica: "Enfócate en la definición primaria y su aplicación práctica directa."
            },
            {
              frente: `¿Qué beneficio directo aporta la implementación de estos conceptos?`,
              dorso: `Permite optimizar los resultados operativos, reducir el margen de error y garantizar el cumplimiento de los estándares de la materia.`,
              pista_didactica: "Piensa en el impacto sobre la calidad, el tiempo y la eficiencia."
            }
          ],
          sintesis: {
            resumen_ejecutivo: `El documento ${cleanTitle} fundamenta la necesidad de estructurar procesos bajo parámetros rigurosos. Se identifican correlaciones clave entre la teoría de base y su implementación contemporánea.`,
            puntos_clave: [
              "Identificación y definición de los conceptos medulares del tema.",
              "Estandarización de criterios según las mejores prácticas del área.",
              "Enfoque adaptado para maximizar la retención según el perfil seleccionado."
            ],
            terminos_clave: ["Fundamentos", "Metodología", "Estructura", "Buenas Prácticas"]
          },
          video: {
            titulo_video: `Masterclass: Claves Esenciales de ${cleanTitle}`,
            duracion: "4:15 min",
            puntos_video: [
              "Min 0:30 - Introducción y contextualización del tema.",
              "Min 1:50 - Análisis de los conceptos primarios y analogías.",
              "Min 3:20 - Aplicación y resolución de dudas frecuentes."
            ]
          },
          quiz: {
            pregunta: `En relación con ${cleanTitle}, ¿cuál de las siguientes opciones describe mejor su propósito esencial?`,
            opciones: [
              "Establecer lineamientos coherentes basados en el análisis riguroso de fuentes.",
              "Limitar el acceso a la información únicamente a especialistas del área.",
              "Descartar cualquier método empírico previo sin evaluación previa.",
              "Aislar los procesos del contexto real de aplicación."
            ],
            correcta: 0,
            explicacion: "El análisis del documento valida que la estructuración rigurosa y fundamentada es el objetivo pedagógico primordial."
          }
        },
        {
          id: "sec_aplicacion_2",
          title: `Aplicaciones Prácticas y Estrategias Avanzadas`,
          summary: `Metodologías de aplicación en situaciones reales, análisis de compensaciones (trade-offs) y criterios de evaluación.`,
          key_concepts: ["Aplicación Práctica", "Estrategia", "Métricas", "Optimización"],
          flashcards: [
            {
              frente: `¿Cómo se evalúa la efectividad de las soluciones en este ámbito?`,
              dorso: `Mediante métricas cuantitativas y cualitativas de rendimiento, coherencia conceptual y alineación con los objetivos estratégicos.`,
              pista_didactica: "Recuerda que lo que no se puede medir difícilmente se puede optimizar."
            }
          ],
          sintesis: {
            resumen_ejecutivo: `La traslación de la teoría a la práctica exige adaptar los métodos a las particularidades del entorno operativo, gestionando riesgos y priorizando la sostenibilidad del sistema.`,
            puntos_clave: [
              "Medición continua y ajuste iterativo de procesos.",
              "Gestión de riesgos y resolución preventiva de cuellos de botella.",
              "Criterios para escalar la solución de manera segura."
            ],
            terminos_clave: ["Escalabilidad", "Métricas", "Optimización", "Rendimiento"]
          },
          video: {
            titulo_video: `Estrategias de Implementación y Casos Reales`,
            duracion: "5:00 min",
            puntos_video: [
              "Min 0:45 - Errores comunes al implementar estas directivas.",
              "Min 2:15 - Casos de estudio y lecciones aprendidas.",
              "Min 4:00 - Guía paso a paso para la adopción exitosa."
            ]
          },
          quiz: {
            pregunta: `¿Cuál es el factor determinante para el éxito a largo plazo al aplicar estos principios?`,
            opciones: [
              "La iteración constante con retroalimentación y medición de impacto.",
              "La rigidez absoluta sin admitir adaptaciones al entorno.",
              "Evitar la documentación y el registro de incidencias.",
              "Depender de un único punto de control sin delegación."
            ],
            correcta: 0,
            explicacion: "La iteración informada por métricas asegura que la estrategia se mantenga relevante y efectiva ante cambios del entorno."
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
    if (nicho && nicho !== 'auto') {
      const map = {
        backend: "Arquitectura de Software",
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
   * Construye el JSON oficial del Hackathon ONE con toda la metadata del pipeline RAG
   */
  buildOfficialJsonPayload(doc, params) {
    const mainSection = doc.sections[0] || {};
    return {
      status: "success",
      pipeline_version: "2.0-adaptativo",
      metadatos: {
        document_id: doc.id,
        filename: doc.filename,
        disciplina: doc.discipline,
        titulo: doc.title,
        perfil: params.perfil,
        formato_salida: params.formato,
        nivel_detalle: params.detalle,
        tiempo_estudio: doc.metadatos?.tiempo_estudio || "8 min",
        fecha_procesamiento: new Date().toISOString()
      },
      evaluacion_calidad: {
        fidelidad_fuente: (doc.metadatos?.anclaje_rag || 99.2) / 100,
        coherencia_pedagogica: 0.985,
        score_global: 0.988,
        chunks_utilizados: doc.metadatos?.chunks_count || 16,
        agente_revisor: "Aprobado sin discrepancias conceptuales"
      },
      almacenamiento_oci: {
        bucket: "nuevamente-processed-docs",
        path: `oci://bucket-nuevamente/docs/${doc.id}.json`,
        status: "persisted_always_free"
      },
      contenido_adaptado: {
        titulo: doc.title,
        disciplina: doc.discipline,
        secciones: doc.sections.map(s => ({
          id: s.id,
          titulo: s.title,
          resumen: s.summary,
          conceptos_clave: s.key_concepts
        })),
        flashcards: mainSection.flashcards || [],
        sintesis: mainSection.sintesis || {},
        video: mainSection.video || {},
        quiz: mainSection.quiz || {}
      }
    };
  }
};
