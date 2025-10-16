class Piano {
    constructor() {
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        this.masterGain = this.audioContext.createGain();
        this.masterGain.connect(this.audioContext.destination);
        this.masterGain.gain.value = 0.5;
        
        this.activeNotes = new Map();
        this.midiData = null;
        this.isPlaying = false;
        this.playbackSpeed = 1.0;
        this.midiTimeouts = [];
        
        this.initPiano();
        this.initControls();
        this.initKeyboard();
    }
    
    // 生成C3到C6的所有音符
    generateNotes() {
        const notes = [];
        const noteNames = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
        
        for (let octave = 3; octave <= 6; octave++) {
            for (let i = 0; i < noteNames.length; i++) {
                if (octave === 6 && i > 0) break; // C6之后停止
                notes.push({
                    name: noteNames[i] + octave,
                    frequency: this.getFrequency(noteNames[i], octave),
                    isBlack: noteNames[i].includes('#'),
                    midi: (octave + 1) * 12 + i
                });
            }
        }
        return notes;
    }
    
    // 计算频率
    getFrequency(note, octave) {
        const A4 = 440;
        const notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
        const semitone = notes.indexOf(note);
        const n = (octave - 4) * 12 + semitone - 9;
        return A4 * Math.pow(2, n / 12);
    }
    
    // 初始化钢琴界面
    initPiano() {
        const piano = document.getElementById('piano');
        const notes = this.generateNotes();
        
        let whiteKeyIndex = 0;
        notes.forEach((note, index) => {
            const key = document.createElement('div');
            key.className = note.isBlack ? 'key black-key' : 'key white-key';
            key.dataset.note = note.name;
            key.dataset.frequency = note.frequency;
            key.dataset.midi = note.midi;

            const whiteWidth = 40;
            const blackWidth = 26;
            
            if (note.isBlack) {
                key.style.left = `${whiteKeyIndex * whiteWidth - (blackWidth / 2)}px`;
            } else {
                whiteKeyIndex++;
            }
            
            const label = document.createElement('span');
            label.className = 'key-label';
            label.textContent = note.name;
            key.appendChild(label);
            
            key.addEventListener('mousedown', () => this.playNote(note.frequency, note.name, key));
            key.addEventListener('mouseup', () => this.stopNote(note.frequency, key));
            key.addEventListener('mouseleave', () => this.stopNote(note.frequency, key));
            
            piano.appendChild(key);
        });
    }
    
    // 播放音符
    playNote(frequency, noteName, keyElement) {
        if (this.activeNotes.has(frequency)) return;
        
        const oscillator = this.audioContext.createOscillator();
        const gainNode = this.audioContext.createGain();
        
        oscillator.type = 'sine';
        oscillator.frequency.value = frequency;
        
        gainNode.gain.setValueAtTime(0, this.audioContext.currentTime);
        gainNode.gain.linearRampToValueAtTime(0.3, this.audioContext.currentTime + 0.01);
        
        oscillator.connect(gainNode);
        gainNode.connect(this.masterGain);
        
        oscillator.start();
        
        this.activeNotes.set(frequency, { oscillator, gainNode });
        keyElement.classList.add('active');
        document.getElementById('currentNote').textContent = `当前音符: ${noteName}`;
    }
    
    // 停止音符
    stopNote(frequency, keyElement) {
        const note = this.activeNotes.get(frequency);
        if (!note) return;
        
        const { oscillator, gainNode } = note;
        gainNode.gain.linearRampToValueAtTime(0, this.audioContext.currentTime + 0.1);
        
        setTimeout(() => {
            oscillator.stop();
            oscillator.disconnect();
            gainNode.disconnect();
        }, 100);
        
        this.activeNotes.delete(frequency);
        keyElement.classList.remove('active');
    }
    
    // 根据MIDI音符号获取频率
    getMidiFrequency(midiNote) {
        return 440 * Math.pow(2, (midiNote - 69) / 12);
    }
    
    // 初始化控制按钮
    initControls() {
        const midiFileInput = document.getElementById('midiFile');
        const playButton = document.getElementById('playMidi');
        const stopButton = document.getElementById('stopMidi');
        const speedControl = document.getElementById('speedControl');
        const volumeControl = document.getElementById('volumeControl');
        
        midiFileInput.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (file) {
                await this.loadMidi(file);
            }
        });
        
        playButton.addEventListener('click', () => this.playMidi());
        stopButton.addEventListener('click', () => this.stopMidi());
        
        speedControl.addEventListener('input', (e) => {
            this.playbackSpeed = parseFloat(e.target.value);
            document.getElementById('speedValue').textContent = `${this.playbackSpeed.toFixed(1)}x`;
        });
        
        volumeControl.addEventListener('input', (e) => {
            this.masterGain.gain.value = parseFloat(e.target.value);
            document.getElementById('volumeValue').textContent = `${Math.round(e.target.value * 100)}%`;
        });
    }
    
    // 加载MIDI文件
    async loadMidi(file) {
        const formData = new FormData();
        formData.append('midiFile', file);
        
        try {
            const response = await fetch('/parse-midi', {
                method: 'POST',
                body: formData
            });
            
            this.midiData = await response.json();
            alert('MIDI文件加载成功!');
            document.getElementById('playMidi').disabled = false;
        } catch (error) {
            alert('MIDI文件加载失败: ' + error.message);
        }
    }
    
    // 播放MIDI
    playMidi() {
        if (!this.midiData || this.isPlaying) return;
        
        this.isPlaying = true;
        document.getElementById('playMidi').disabled = true;
        
        const track = this.midiData.track[1] || this.midiData.track[0];
        const ticksPerBeat = this.midiData.timeDivision;
        const microsecondsPerBeat = 500000; // 默认120 BPM
        const msPerTick = (microsecondsPerBeat / ticksPerBeat / 1000) / this.playbackSpeed;
        
        let currentTime = 0;
        
        track.event.forEach(event => {
            currentTime += event.deltaTime * msPerTick;
            
            if (event.type === 9 && event.data[1] > 0) { // Note On
                const timeout = setTimeout(() => {
                    const midiNote = event.data[0];
                    const frequency = this.getMidiFrequency(midiNote);
                    const keyElement = document.querySelector(`[data-midi="${midiNote}"]`);
                    
                    if (keyElement) {
                        this.playNote(frequency, keyElement.dataset.note, keyElement);
                    }
                }, currentTime);
                
                this.midiTimeouts.push(timeout);
            } else if (event.type === 8 || (event.type === 9 && event.data[1] === 0)) { // Note Off
                const timeout = setTimeout(() => {
                    const midiNote = event.data[0];
                    const frequency = this.getMidiFrequency(midiNote);
                    const keyElement = document.querySelector(`[data-midi="${midiNote}"]`);
                    
                    if (keyElement) {
                        this.stopNote(frequency, keyElement);
                    }
                }, currentTime);
                
                this.midiTimeouts.push(timeout);
            }
        });
        
        // 播放结束
        const finalTimeout = setTimeout(() => {
            this.stopMidi();
        }, currentTime + 1000);
        
        this.midiTimeouts.push(finalTimeout);
    }
    
    // 停止MIDI播放
    stopMidi() {
        this.midiTimeouts.forEach(timeout => clearTimeout(timeout));
        this.midiTimeouts = [];
        
        // 停止所有正在播放的音符
        document.querySelectorAll('.key.active').forEach(key => {
            const frequency = parseFloat(key.dataset.frequency);
            this.stopNote(frequency, key);
        });
        
        this.isPlaying = false;
        document.getElementById('playMidi').disabled = false;
    }
    
    // 键盘快捷键
    initKeyboard() {
        const keyMap = {
            'a': 'C3', 'w': 'C#3', 's': 'D3', 'e': 'D#3', 'd': 'E3',
            'f': 'F3', 't': 'F#3', 'g': 'G3', 'y': 'G#3', 'h': 'A3', 'u': 'A#3', 'j': 'B3',
            'k': 'C4', 'o': 'C#4', 'l': 'D4'
        };
        
        document.addEventListener('keydown', (e) => {
            const note = keyMap[e.key.toLowerCase()];
            if (note && !e.repeat) {
                const keyElement = document.querySelector(`[data-note="${note}"]`);
                if (keyElement) {
                    const frequency = parseFloat(keyElement.dataset.frequency);
                    this.playNote(frequency, note, keyElement);
                }
            }
        });
        
        document.addEventListener('keyup', (e) => {
            const note = keyMap[e.key.toLowerCase()];
            if (note) {
                const keyElement = document.querySelector(`[data-note="${note}"]`);
                if (keyElement) {
                    const frequency = parseFloat(keyElement.dataset.frequency);
                    this.stopNote(frequency, keyElement);
                }
            }
        });
    }
}

// 初始化钢琴
window.addEventListener('DOMContentLoaded', () => {
    new Piano();
});
