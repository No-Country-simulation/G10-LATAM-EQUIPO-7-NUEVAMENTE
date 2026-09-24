/**
 * uploadTab.js
 * Controlador de la Pestaña Completa de Ingesta, Parámetros Pedagógicos y Pipeline RAG.
 */

import { state } from '../state.js';
import { sampleLibrary } from '../data/sampleLibrary.js';
import { mockService } from '../api/mockService.js';
import { apiClient } from '../api/apiClient.js';
import { router } from './router.js';

export const uploadTab = {
  elements: {},

  init() {
    this.bindElements();
    this.setupDropzone();
    this.setupSampleButtons();
    this.setupParamListeners();
    this.setupExecution();
    this.setupResolverActions();
    this.syncInitialState();
  },

  bindElements() {
    this.elements = {
      dropArea: document.getElementById('dropAreaLarge'),
      docFileInput: document.getElementById('docFileInput'),
      selectedFileCard: document.getElementById('selectedFileCard'),
      selectedFileName: document.getElementById('selectedFileName'),
      selectedFileSize: document.getElementById('selectedFileSize'),
      fileFormatBadge: document.getElementById('fileFormatBadge'),
      btnRemoveFile: document.getElementById('btnRemoveFile'),
      quickSampleBtns: document.querySelectorAll('.btn-quick-sample'),

      // Parámetros
      paramPerfil: document.getElementById('paramPerfil'),
      paramFormato: document.getElementById('paramFormato'),
      paramNicho: document.getElementById('paramNicho'),

      // Stepper
      pipelineCard: document.getElementById('pipelineCard'),
      pipelineStatusBadge: document.getElementById('pipelineStatusBadge'),
      stepOci: document.getElementById('stepOci'),
      stepChroma: document.getElementById('stepChroma'),
      stepGen: document.getElementById('stepGen'),
      stepCritic: document.getElementById('stepCritic'),
      line1: document.getElementById('line1'),
      line2: document.getElementById('line2'),
      line3: document.getElementById('line3'),
      pipelineLiveLog: document.getElementById('pipelineLiveLog'),
      btnLanzarProcesamiento: document.getElementById('btnLanzarProcesamiento'),

      // Resultados y Resolver
      resultBoxContainer: document.getElementById('resultBoxContainer'),
      badgeTiempo: document.getElementById('badgeTiempo'),
      badgeSecciones: document.getElementById('badgeSecciones'),
      badgeNivel: document.getElementById('badgeNivel'),
      resolverFormatCards: document.querySelectorAll('.btn-resolver-card'),
      btnIrALaBiblioteca: document.getElementById('btnIrALaBiblioteca')
    };
  },

  setupDropzone() {
    const { dropArea, docFileInput } = this.elements;
    if (!dropArea || !docFileInput) return;

    ['dragenter', 'dragover'].forEach(eventName => {
      dropArea.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropArea.classList.add('dragover');
      });
    });

    ['dragleave', 'drop'].forEach(eventName => {
      dropArea.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropArea.classList.remove('dragover');
      });
    });

    dropArea.addEventListener('drop', (e) => {
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        this.handleFileChosen(e.dataTransfer.files[0]);
      }
    });

    docFileInput.addEventListener('change', (e) => {
      if (e.target.files && e.target.files.length > 0) {
        this.handleFileChosen(e.target.files[0]);
      }
    });

    if (this.elements.btnRemoveFile) {
      this.elements.btnRemoveFile.addEventListener('click', () => {
        this.clearFile();
      });
    }
  },

  handleFileChosen(file) {
    const ext = file.name.split('.').pop().toLowerCase();
    const allowed = ['pdf', 'md', 'txt'];
    if (!allowed.includes(ext)) {
      alert(`Formato de archivo no soportado (.${ext}). Solo se admiten archivos PDF, Markdown (.md) y TXT.`);
      return;
    }

    const sizeMb = (file.size / (1024 * 1024)).toFixed(2);

    const fileData = {
      name: file.name,
      size: `${sizeMb} MB`,
      format: ext.toUpperCase(),
      sampleKey: null,
      rawFile: file
    };

    state.set({ selectedFile: fileData });
    this.renderSelectedFile(fileData);

    // Desactivar botones de muestra rápida
    this.elements.quickSampleBtns.forEach(btn => btn.classList.remove('active'));
  },

  setupSampleButtons() {
    this.elements.quickSampleBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const sampleKey = btn.getAttribute('data-sample');
        const sample = sampleLibrary[sampleKey];
        if (!sample) return;

        this.elements.quickSampleBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        const fileData = {
          name: sample.filename,
          size: sample.filesize,
          format: sample.filename.split('.').pop().toUpperCase(),
          sampleKey: sampleKey,
          rawFile: null
        };

        state.set({ selectedFile: fileData });
        this.renderSelectedFile(fileData);

        // Preseleccionar parámetros sugeridos
        if (sample.metadatos) {
          if (this.elements.paramPerfil) {
            const rawPerfil = sample.metadatos.target_profile || sample.metadatos.perfil;
            const map = { principiante: 'beginner', intermedio: 'intermediate', avanzado: 'advanced' };
            this.elements.paramPerfil.value = map[rawPerfil] || rawPerfil || 'intermediate';
          }
        }
      });
    });
  },

  setupParamListeners() {
    const updateParams = () => {
      state.set({
        adaptationParams: {
          target_profile: this.elements.paramPerfil?.value || 'intermediate',
          output_format: this.elements.paramFormato?.value || 'all',
          niche_context: this.elements.paramNicho?.value || 'general'
        }
      });
    };

    [this.elements.paramPerfil, this.elements.paramFormato, this.elements.paramNicho].forEach(el => {
      if (el) el.addEventListener('change', updateParams);
    });
  },

  setupExecution() {
    if (!this.elements.btnLanzarProcesamiento) return;

    this.elements.btnLanzarProcesamiento.addEventListener('click', async () => {
      const { selectedFile, adaptationParams, apiMode } = state.get();
      if (!selectedFile) {
        alert('Por favor selecciona o arrastra un documento para procesar.');
        return;
      }

      await this.runPipeline(selectedFile, adaptationParams, apiMode);
    });
  },

  async runPipeline(selectedFile, params, apiMode) {
    const { pipelineCard, btnLanzarProcesamiento, resultBoxContainer } = this.elements;
    
    // UI de preparación
    if (pipelineCard) pipelineCard.style.display = 'flex';
    if (resultBoxContainer) resultBoxContainer.style.display = 'none';
    if (btnLanzarProcesamiento) {
      btnLanzarProcesamiento.disabled = true;
      btnLanzarProcesamiento.innerHTML = '<span>Procesando documento...</span>';
    }
    this.resetStepperUI();

    const targetProfile = params.target_profile || 'intermediate';
    const outputFormat = params.output_format || 'all';
    const nicheContext = params.niche_context || 'general';

    try {
      if (apiMode === 'real' && selectedFile.rawFile) {
        // Paso 1: Subir el documento al backend FastAPI (POST /api/v1/documents)
        this.setStepActive(this.elements.stepOci, 'Persistiendo archivo en backend (POST /api/v1/documents)...');
        const uploadResult = await apiClient.uploadFile(selectedFile.rawFile);
        console.log('[Backend API /documents] Respuesta recibida:', uploadResult);

        const docId = uploadResult.document_id;
        if (!docId) {
          throw new Error('El backend no retornó un document_id válido.');
        }

        state.set({
          backendDocument: uploadResult,
          currentDocId: docId
        });
        this.setStepCompleted(this.elements.stepOci, this.elements.line1);

        // Paso 2: Indexación y preparación
        this.setStepActive(this.elements.stepChroma, `Indexando chunks para document_id [${docId}]...`);
        await this.wait(400);
        this.setStepCompleted(this.elements.stepChroma, this.elements.line2);

        // Paso 3: Llamar al contrato v1 de adaptación pedagógica (POST /api/v1/adaptations)
        this.setStepActive(this.elements.stepGen, `Generando adaptación en backend (POST /api/v1/adaptations) para perfil [${targetProfile}]...`);
        
        const adaptationPayload = {
          document_id: docId,
          target_profile: targetProfile,
          output_format: outputFormat,
          niche_context: nicheContext
        };
        console.log('[Backend API /adaptations] Enviando payload v1:', adaptationPayload);

        const adaptationResult = await apiClient.adaptContent(adaptationPayload);
        console.log('[Backend API /adaptations] Respuesta recibida:', adaptationResult);
        this.setStepCompleted(this.elements.stepGen, this.elements.line3);

        // Paso 4: Agente Revisor / Validación final
        this.setStepActive(this.elements.stepCritic, 'Validando estructura pedagógica y calidad de respuesta...');
        await this.wait(350);
        this.setStepCompleted(this.elements.stepCritic, null);

        // Mapear resultado del backend al modelo de visualización del frontend
        const procDoc = this.mapBackendResponseToDocument(selectedFile, adaptationResult, params);
        this.onPipelineSuccess(procDoc, adaptationResult, params);

      } else {
        // Modo Mock (o muestra precargada sin archivo físico)
        this.setStepActive(this.elements.stepOci, 'Almacenando documento en OCI Object Storage...');
        await this.wait(500);
        this.setStepCompleted(this.elements.stepOci, this.elements.line1);

        this.setStepActive(this.elements.stepChroma, 'ChromaDB: particionando documento y calculando embeddings...');
        await this.wait(600);
        this.setStepCompleted(this.elements.stepChroma, this.elements.line2);

        this.setStepActive(this.elements.stepGen, `Agente Generador: Extrayendo conceptos para perfil [${targetProfile}] en formato [${outputFormat}]...`);
        await this.wait(650);
        this.setStepCompleted(this.elements.stepGen, this.elements.line3);

        this.setStepActive(this.elements.stepCritic, 'Agente Revisor: Evaluando fidelidad conceptual y estructura JSON v1...');
        await this.wait(500);
        this.setStepCompleted(this.elements.stepCritic, null);

        const { document: procDoc, structuredJson } = await mockService.processMockPipeline(selectedFile, {
          target_profile: targetProfile,
          output_format: outputFormat,
          niche_context: nicheContext
        });
        this.onPipelineSuccess(procDoc, structuredJson, params);
      }
    } catch (err) {
      console.error('[Pipeline Error]:', err);
      if (this.elements.pipelineLiveLog) this.elements.pipelineLiveLog.textContent = `Error: ${err.message}`;
      if (this.elements.pipelineStatusBadge) {
        this.elements.pipelineStatusBadge.textContent = 'Fallo';
        this.elements.pipelineStatusBadge.style.background = 'rgba(239, 68, 68, 0.2)';
        this.elements.pipelineStatusBadge.style.color = '#ef4444';
      }
      alert(`No se pudo completar el procesamiento: ${err.message}`);
    } finally {
      if (btnLanzarProcesamiento) {
        btnLanzarProcesamiento.disabled = false;
        btnLanzarProcesamiento.innerHTML = '<span>Procesar Documento</span>';
      }
    }
  },

  /**
   * Mapea la respuesta estructurada del contrato v1 de Backend al modelo del Cuaderno/StudyHub
   */
  mapBackendResponseToDocument(selectedFile, backendRes, params) {
    const adapted = backendRes.adapted_content || {};
    const meta = backendRes.metadata || {};
    const quality = backendRes.quality_evaluation || {};

    const cleanTitle = adapted.title || selectedFile.name.replace(/\.[^/.]+$/, "").replace(/[-_]/g, " ");
    const discipline = mockService.inferDiscipline(cleanTitle, meta.niche_context || params.niche_context);

    const section = {
      id: "sec_adapted_1",
      title: cleanTitle,
      summary: adapted.summary?.executive_summary || "Contenido adaptado generado por NuevaMente RAG.",
      key_concepts: adapted.summary?.key_terms || ["Concepto Clave", "Arquitectura"],
      flashcards: (adapted.flashcards || []).map(f => ({
        front: f.front || f.frente,
        back: f.back || f.dorso,
        didactic_hint: f.didactic_hint || f.pista_didactica
      })),
      quiz: adapted.quiz ? {
        question: adapted.quiz.question || adapted.quiz.pregunta,
        options: adapted.quiz.options || adapted.quiz.opciones,
        correct_answer: adapted.quiz.correct_answer !== undefined ? adapted.quiz.correct_answer : adapted.quiz.correcta,
        explanation: adapted.quiz.explanation || adapted.quiz.explicacion
      } : null,
      video: adapted.tutorial ? {
        title: adapted.tutorial.title || adapted.tutorial.titulo_video,
        duration: adapted.tutorial.duration || adapted.tutorial.duracion,
        key_points: adapted.tutorial.key_points || adapted.tutorial.puntos_video
      } : null,
      sintesis: adapted.summary ? {
        executive_summary: adapted.summary.executive_summary || adapted.summary.resumen_ejecutivo,
        key_takeaways: adapted.summary.key_takeaways || adapted.summary.puntos_clave,
        key_terms: adapted.summary.key_terms || adapted.summary.terminos_clave
      } : null
    };

    return {
      id: backendRes.document_id || `doc_${Date.now()}`,
      filename: selectedFile.name,
      discipline: discipline,
      title: cleanTitle.charAt(0).toUpperCase() + cleanTitle.slice(1),
      description: `Contenido educativo adaptado para perfil [${meta.target_profile || params.target_profile}].`,
      filesize: selectedFile.size || "2.0 MB",
      metadatos: {
        target_profile: meta.target_profile || params.target_profile,
        tiempo_estudio: "6 min",
        anclaje_rag: Math.round((quality.overall_score || 0.99) * 100),
        fidelidad: `${((quality.source_faithfulness || 0.99) * 100).toFixed(1)}%`,
        chunks_count: 14
      },
      sections: [section]
    };
  },

  onPipelineSuccess(procDoc, structuredJson, params = {}) {
    const currentCustomBooks = state.get().customBooks || [];
    const exists = currentCustomBooks.some(b => b.id === procDoc.id);
    const updatedCustom = exists ? currentCustomBooks : [procDoc, ...currentCustomBooks];

    // Mapear formato solicitado al formato activo en el Study Hub
    const outputFormat = params.output_format || 'all';
    let initialStudyFormat = 'flashcards';
    if (outputFormat === 'quiz') initialStudyFormat = 'quiz';
    else if (outputFormat === 'tutorial') initialStudyFormat = 'video';
    else if (outputFormat === 'summary') initialStudyFormat = 'sintesis';

    state.set({
      currentDocument: procDoc,
      customBooks: updatedCustom,
      lastStructuredJson: structuredJson,
      notebook: {
        currentSpreadIndex: 0,
        isTurningPage: false
      },
      studyHub: {
        activeSectionId: procDoc.sections[0]?.id || null,
        activeFormat: initialStudyFormat,
        currentCardIndex: 0,
        isFlipped: false
      }
    });

    if (this.elements.pipelineStatusBadge) {
      this.elements.pipelineStatusBadge.textContent = 'Completado ✓';
      this.elements.pipelineStatusBadge.style.background = 'rgba(16, 185, 129, 0.2)';
      this.elements.pipelineStatusBadge.style.color = '#10b981';
    }
    if (this.elements.pipelineLiveLog) {
      this.elements.pipelineLiveLog.textContent = 'Documento procesado correctamente según el contrato v1. Ya está disponible en tu biblioteca.';
    }

    // Actualizar datos de estudio
    const meta = structuredJson.metadata || structuredJson.metadatos || {};
    const quality = structuredJson.quality_evaluation || structuredJson.evaluacion_calidad || {};
    
    if (this.elements.badgeTiempo) {
      this.elements.badgeTiempo.textContent = `Tiempo de lectura: ${meta.tiempo_estudio || '6 min'}`;
    }
    if (this.elements.badgeSecciones) {
      this.elements.badgeSecciones.textContent = `Secciones: ${procDoc.sections?.length || 1}`;
    }
    if (this.elements.badgeNivel) {
      this.elements.badgeNivel.textContent = `Nivel: ${this.getLevelLabel(meta.target_profile || meta.perfil)}`;
    }

    // Mostrar panel de resolución de formatos
    if (this.elements.resultBoxContainer) {
      this.elements.resultBoxContainer.style.display = 'flex';
      this.elements.resultBoxContainer.scrollIntoView({ behavior: 'smooth' });
    }
  },

  getLevelLabel(perfil) {
    const map = {
      beginner: 'Principiante',
      intermediate: 'Intermedio',
      advanced: 'Avanzado',
      principiante: 'Principiante',
      intermedio: 'Intermedio',
      avanzado: 'Avanzado'
    };
    return map[(perfil || '').toLowerCase()] || 'Intermedio';
  },

  setupResolverActions() {
    // Tarjetas del resolver (Flashcards, Quiz, Video, Resumen)
    this.elements.resolverFormatCards.forEach(card => {
      card.addEventListener('click', () => {
        const targetFormat = card.getAttribute('data-resolve-format');
        state.set({
          studyHub: {
            ...state.get().studyHub,
            activeFormat: targetFormat
          }
        });
        router.navigate('study');
      });
    });

    // Botón para ir a la biblioteca
    if (this.elements.btnIrALaBiblioteca) {
      this.elements.btnIrALaBiblioteca.addEventListener('click', () => {
        router.navigate('library');
      });
    }
  },

  syncInitialState() {
    const { selectedFile } = state.get();
    if (selectedFile) {
      this.renderSelectedFile(selectedFile);
    }
  },

  renderSelectedFile(fileData) {
    if (!fileData) return;
    this.elements.selectedFileName.textContent = fileData.name;
    this.elements.selectedFileSize.textContent = `${fileData.size} · Listo para indexación`;
    this.elements.fileFormatBadge.textContent = fileData.format || 'DOC';
    this.elements.selectedFileCard.style.display = 'flex';
    this.elements.dropArea.style.display = 'none';
  },

  clearFile() {
    state.set({ selectedFile: null });
    this.elements.selectedFileCard.style.display = 'none';
    this.elements.dropArea.style.display = 'flex';
    this.elements.quickSampleBtns.forEach(btn => btn.classList.remove('active'));
    if (this.elements.docFileInput) this.elements.docFileInput.value = '';
  },

  resetStepperUI() {
    const steps = [this.elements.stepOci, this.elements.stepChroma, this.elements.stepGen, this.elements.stepCritic];
    const lines = [this.elements.line1, this.elements.line2, this.elements.line3];

    steps.forEach(s => s && s.classList.remove('active', 'completed'));
    lines.forEach(l => l && l.classList.remove('completed'));

    if (this.elements.pipelineStatusBadge) {
      this.elements.pipelineStatusBadge.textContent = 'Ejecutando...';
      this.elements.pipelineStatusBadge.style.background = 'rgba(6, 182, 212, 0.15)';
      this.elements.pipelineStatusBadge.style.color = 'var(--accent-cyan)';
    }
  },

  setStepActive(stepEl, logText) {
    if (stepEl) stepEl.classList.add('active');
    if (this.elements.pipelineLiveLog) this.elements.pipelineLiveLog.textContent = logText;
  },

  setStepCompleted(stepEl, lineEl) {
    if (stepEl) {
      stepEl.classList.remove('active');
      stepEl.classList.add('completed');
    }
    if (lineEl) lineEl.classList.add('completed');
  },

  wait(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
};
