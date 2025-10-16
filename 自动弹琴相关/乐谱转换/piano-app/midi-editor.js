class MidiEditor {
    constructor() {
        this.midiData = null;
        this.currentTrack = 0;
        this.selectedNotes = new Set();
        this.pixelsPerTick = 0.1;
        this.isDragging = false;
        this.draggedNote = null;
        
        // 音频播放相关
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        this.player = new WebAudioFontPlayer();
        this.instrument = _tone_0250_SoundBlasterOld_sf2;
        this.player.loader.decodeAfterLoading(this.audioContext, '_tone_0250_SoundBlasterOld_sf2');
        this.isPlaying = false;
        this.playbackTimeouts = [];
        
        this.initElements();
        this.initEventListeners();
        this.renderPianoRoll();
    }
    
    initElements() {
        this.pianoRoll = document.getElementById('pianoRoll');
        this.pianoRollContent = document.getElementById('pianoRollContent');
        this.trackSelect = document.getElementById('trackSelect');
        this.noteNumber = document.getElementById('noteNumber');
        this.noteTime = document.getElementById('noteTime');
        this.noteDuration = document.getElementById('noteDuration');
        this.noteVelocity = document.getElementById('noteVelocity');
        this.zoomControl = document.getElementById('zoomControl');
        this.zoomValue = document.getElementById('zoomValue');
    }
    
    initEventListeners() {
        document.getElementById('midiFileInput').addEventListener('change', (e) => this.loadMidiFile(e));
        document.getElementById('saveBtn').addEventListener('click', () => this.saveMidi());
        document.getElementById('addNoteBtn').addEventListener('click', () => this.addNote());
        document.getElementById('deleteNoteBtn').addEventListener('click', () => this.deleteSelectedNotes());
        document.getElementById('updateNoteBtn').addEventListener('click', () => this.updateSelectedNote());
        document.getElementById('playBtn').addEventListener('click', () => this.playCurrentTrack());
        document.getElementById('stopBtn').addEventListener('click', () => this.stopPlayback());
        
        this.trackSelect.addEventListener('change', (e) => {
            this.currentTrack = parseInt(e.target.value);
            this.renderNotes();
        });

        this.zoomControl.addEventListener('input', (e) => {
            this.pixelsPerTick = parseFloat(e.target.value);
            const zoomLevel = (this.pixelsPerTick / 0.1).toFixed(1);
            this.zoomValue.textContent = `${zoomLevel}x`;
            this.renderNotes();
        });

        // 键盘快捷键
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Delete' || e.key === 'Backspace') {
                if (this.selectedNotes.size > 0) {
                    e.preventDefault();
                    this.deleteSelectedNotes();
                }
            }
            if (e.ctrlKey || e.metaKey) {
                if (e.key === 'a') {
                    e.preventDefault();
                    this.selectAllNotes();
                }
                if (e.key === 's') {
                    e.preventDefault();
                    this.saveMidi();
                }
            }
        });
    }
    
    async loadMidiFile(event) {
        const file = event.target.files[0];
        if (!file) return;
        
        const formData = new FormData();
        formData.append('midiFile', file);
        
        try {
            const response = await fetch('/midi-to-json', {
                method: 'POST',
                body: formData
            });
            
            this.midiData = await response.json();
            this.updateTrackSelector();
            this.renderNotes();
            this.enableControls();
            alert('MIDI 文件加载成功!');
        } catch (error) {
            console.error('加载失败:', error);
            alert('加载 MIDI 文件失败: ' + error.message);
        }
    }

    enableControls() {
        document.getElementById('playBtn').disabled = false;
        document.getElementById('stopBtn').disabled = false;
        document.getElementById('saveBtn').disabled = false;
        document.getElementById('addNoteBtn').disabled = false;
        document.getElementById('deleteNoteBtn').disabled = false;
        document.getElementById('updateNoteBtn').disabled = false;
        document.getElementById('trackSelect').disabled = false;
        document.getElementById('zoomControl').disabled = false;
        document.getElementById('noteNumber').disabled = false;
        document.getElementById('noteTime').disabled = false;
        document.getElementById('noteDuration').disabled = false;
        document.getElementById('noteVelocity').disabled = false;
    }
    
    updateTrackSelector() {
        this.trackSelect.innerHTML = '';
        this.midiData.tracks.forEach((track, index) => {
            const option = document.createElement('option');
            option.value = index;
            option.textContent = `音轨 ${index + 1} (${track.notes.length} 个音符)`;
            this.trackSelect.appendChild(option);
        });
    }
    
    renderPianoRoll() {
        const noteNames = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
        const blackKeys = [1, 3, 6, 8, 10];
        
        this.pianoRollContent.innerHTML = '';
        
        for (let i = 127; i >= 0; i--) {
            const row = document.createElement('div');
            row.className = 'note-row';
            row.dataset.note = i;
            
            const noteIndex = i % 12;
            if (blackKeys.includes(noteIndex)) {
                row.classList.add('black-key');
            }
            
            if (i % 12 === 0) {
                row.classList.add('octave-start');
            }
            
            this.pianoRollContent.appendChild(row);
        }
    }
    
    renderNotes() {
        if (!this.midiData || !this.midiData.tracks[this.currentTrack]) return;
        
        document.querySelectorAll('.note-block').forEach(el => el.remove());
        
        const track = this.midiData.tracks[this.currentTrack];
        
        track.notes.forEach((note, index) => {
            const noteBlock = document.createElement('div');
            noteBlock.className = 'note-block';
            noteBlock.dataset.noteIndex = index;
            
            const left = note.time * this.pixelsPerTick;
            const width = Math.max(note.duration * this.pixelsPerTick, 5);
            
            noteBlock.style.left = left + 'px';
            noteBlock.style.width = width + 'px';
            noteBlock.style.top = (127 - note.note) * 20 + 'px';
            
            noteBlock.addEventListener('click', (e) => {
                e.stopPropagation();
                this.selectNote(index, e.ctrlKey || e.metaKey);
            });
            
            noteBlock.addEventListener('mousedown', (e) => {
                if (e.button === 0) {
                    this.startDrag(e, note, index);
                }
            });
            
            this.pianoRollContent.appendChild(noteBlock);
        });
        
        this.updateSelection();
    }
    
    selectNote(index, multiSelect = false) {
        if (!multiSelect) {
            this.selectedNotes.clear();
        }
        
        if (this.selectedNotes.has(index)) {
            this.selectedNotes.delete(index);
        } else {
            this.selectedNotes.add(index);
        }
        
        this.updateSelection();
        this.updateNoteInfo();
    }

    selectAllNotes() {
        if (!this.midiData || !this.midiData.tracks[this.currentTrack]) return;
        
        this.selectedNotes.clear();
        const track = this.midiData.tracks[this.currentTrack];
        track.notes.forEach((_, index) => this.selectedNotes.add(index));
        this.updateSelection();
        this.updateNoteInfo();
    }
    
    updateSelection() {
        document.querySelectorAll('.note-block').forEach(block => {
            const index = parseInt(block.dataset.noteIndex);
            if (this.selectedNotes.has(index)) {
                block.classList.add('selected');
            } else {
                block.classList.remove('selected');
            }
        });
    }
    
    updateNoteInfo() {
        if (this.selectedNotes.size === 1) {
            const index = Array.from(this.selectedNotes)[0];
            const note = this.midiData.tracks[this.currentTrack].notes[index];
            
            this.noteNumber.value = note.note;
            this.noteTime.value = note.time;
            this.noteDuration.value = note.duration;
            this.noteVelocity.value = note.velocity;
        } else if (this.selectedNotes.size > 1) {
            this.noteNumber.value = `${this.selectedNotes.size} 个音符`;
            this.noteTime.value = '';
            this.noteDuration.value = '';
            this.noteVelocity.value = '';
        } else {
            this.noteNumber.value = '';
            this.noteTime.value = '';
            this.noteDuration.value = '';
            this.noteVelocity.value = '';
        }
    }
    
    updateSelectedNote() {
        if (this.selectedNotes.size !== 1) {
            alert('请选择一个音符进行编辑');
            return;
        }
        
        const index = Array.from(this.selectedNotes)[0];
        const note = this.midiData.tracks[this.currentTrack].notes[index];
        
        note.note = parseInt(this.noteNumber.value);
        note.time = parseInt(this.noteTime.value);
        note.duration = parseInt(this.noteDuration.value);
        note.velocity = parseInt(this.noteVelocity.value);
        
        this.renderNotes();
    }
    
    addNote() {
        if (!this.midiData) {
            alert('请先加载 MIDI 文件');
            return;
        }
        
        const newNote = {
            note: 60,
            time: 0,
            duration: this.midiData.timeDivision || 480,
            velocity: 80,
            channel: 0
        };
        
        this.midiData.tracks[this.currentTrack].notes.push(newNote);
        this.renderNotes();
    }
    
    deleteSelectedNotes() {
        if (this.selectedNotes.size === 0) {
            alert('请先选择要删除的音符');
            return;
        }
        
        const track = this.midiData.tracks[this.currentTrack];
        const indicesToDelete = Array.from(this.selectedNotes).sort((a, b) => b - a);
        
        indicesToDelete.forEach(index => {
            track.notes.splice(index, 1);
        });
        
        this.selectedNotes.clear();
        this.renderNotes();
    }

    playCurrentTrack() {
        if (!this.midiData || this.isPlaying) return;

        this.isPlaying = true;
        document.getElementById('playBtn').disabled = true;
        
        const track = this.midiData.tracks[this.currentTrack];
        const notes = [...track.notes].sort((a, b) => a.time - b.time);
        
        const startTime = this.audioContext.currentTime;
        const ticksPerBeat = this.midiData.timeDivision;
        const secondsPerTick = 0.0005;
        
        notes.forEach(note => {
            const playTime = startTime + (note.time * secondsPerTick);
            const duration = note.duration * secondsPerTick;
            
            const timeout = setTimeout(() => {
                this.player.queueWaveTable(
                    this.audioContext,
                    this.audioContext.destination,
                    this.instrument,
                    this.audioContext.currentTime,
                    note.note,
                    duration,
                    note.velocity / 127
                );
                
                const block = document.querySelector(`[data-note-index="${notes.indexOf(note)}"]`);
                if (block) {
                    block.style.filter = 'brightness(1.5)';
                    setTimeout(() => {
                        block.style.filter = '';
                    }, duration * 1000);
                }
            }, (playTime - startTime) * 1000);
            
            this.playbackTimeouts.push(timeout);
        });
        
        if (notes.length > 0) {
            const lastNote = notes[notes.length - 1];
            const totalDuration = (lastNote.time + lastNote.duration) * secondsPerTick;
            const endTimeout = setTimeout(() => {
                this.stopPlayback();
            }, totalDuration * 1000 + 500);
            this.playbackTimeouts.push(endTimeout);
        }
    }

    stopPlayback() {
        this.playbackTimeouts.forEach(timeout => clearTimeout(timeout));
        this.playbackTimeouts = [];
        this.player.cancelQueue(this.audioContext);
        this.isPlaying = false;
        document.getElementById('playBtn').disabled = false;
        
        document.querySelectorAll('.note-block').forEach(block => {
            block.style.filter = '';
        });
    }
    
    async saveMidi() {
        if (!this.midiData) {
            alert('没有可保存的 MIDI 数据');
            return;
        }
        
        try {
            const response = await fetch('/save-midi', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    midiData: this.midiData,
                    fileName: 'edited.mid'
                })
            });
            
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'edited.mid';
                a.click();
                window.URL.revokeObjectURL(url);
            }
        } catch (error) {
            console.error('保存失败:', error);
            alert('保存 MIDI 文件失败: ' + error.message);
        }
    }
    
    startDrag(e, note, noteIndex) {
        this.isDragging = true;
        this.draggedNoteIndex = noteIndex;
        this.dragStartX = e.clientX;
        this.dragStartY = e.clientY;
        this.originalTime = note.time;
        this.originalNote = note.note;
        
        const onMouseMove = (e) => {
            if (!this.isDragging) return;
            
            const deltaX = e.clientX - this.dragStartX;
            const deltaY = e.clientY - this.dragStartY;
            
            const newTime = Math.max(0, this.originalTime + deltaX / this.pixelsPerTick);
            const newNote = Math.max(0, Math.min(127, this.originalNote - Math.round(deltaY / 20)));
            
            note.time = Math.round(newTime);
            note.note = newNote;
            
            this.renderNotes();
        };
        
        const onMouseUp = () => {
            this.isDragging = false;
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
            this.updateNoteInfo();
        };
        
        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);
    }
}

window.addEventListener('DOMContentLoaded', () => {
    new MidiEditor();
});
