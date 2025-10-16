class Piano {
    constructor() {
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        this.player = new WebAudioFontPlayer();
        this.instrument = _tone_0250_SoundBlasterOld_sf2;

        // 加载钢琴音色
        this.player.loader.decodeAfterLoading(this.audioContext, '_tone_0250_SoundBlasterOld_sf2');

        // 预加载音符（C3-C6 对应 MIDI 48-84）
        for (let i = 48; i <= 84; i++) {
            this.player.adjustPreset(this.audioContext, this.instrument, i);
        }

        this.activeEnvelopes = new Map();
        this.isPlaying = false;
        this.playbackSpeed = 1.0;
        this.volume = 0.5;
        this.midiTimeouts = [];

        this.initPianoUI();
        this.initControls();
        this.initKeyboard();
    }

    generateNotes() {
        const notes = [];
        const noteNames = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];

        for (let octave = 3; octave <= 6; octave++) {
            for (let i = 0; i < noteNames.length; i++) {
                if (octave === 6 && i > 0) break;
                const name = noteNames[i] + octave;
                const midi = (octave + 1) * 12 + i;
                notes.push({ name, midi, isBlack: noteNames[i].includes('#') });
            }
        }
        return notes;
    }

    // 初始化钢琴界面
    initPianoUI() {
        const piano = document.getElementById('piano');
        const notes = this.generateNotes();
        let whiteKeyIndex = 0;
        const WHITE_KEY_WIDTH = 40;
        const BLACK_KEY_WIDTH = 26;

        notes.forEach(note => {
            const key = document.createElement('div');
            key.className = note.isBlack ? 'key black-key' : 'key white-key';
            key.dataset.note = note.name;
            key.dataset.midi = note.midi;

            // 只给黑键设置绝对位置
            if (note.isBlack) {
                key.style.left = `${whiteKeyIndex * WHITE_KEY_WIDTH - BLACK_KEY_WIDTH / 2}px`;
            } else {
                whiteKeyIndex++;
            }

            const label = document.createElement('span');
            label.className = 'key-label';
            label.textContent = note.name;
            key.appendChild(label);

            key.addEventListener('mousedown', () => this.playNote(note.midi, note.name, key));
            key.addEventListener('mouseup', () => this.stopNote(note.midi, key));
            key.addEventListener('mouseleave', () => this.stopNote(note.midi, key));

            piano.appendChild(key);
        });
    }

    playNote(midi, noteName, keyElement) {
        if (this.activeEnvelopes.has(midi)) return;

        // 使用 WebAudioFont 播放音符
        const envelope = this.player.queueWaveTable(
            this.audioContext,
            this.audioContext.destination,
            this.instrument,
            0, // 立即播放
            midi, // MIDI 音符编号
            9999, // 持续时间（直到手动停止）
            this.volume // 音量
        );

        this.activeEnvelopes.set(midi, envelope);
        keyElement.classList.add('active'); // 高亮显示按下的键
        document.getElementById('currentNote').textContent = `当前音符: ${noteName}`; // 显示当前音符名称
    }

    stopNote(midi, keyElement) {
        const envelope = this.activeEnvelopes.get(midi);
        if (!envelope) return;

        // 停止音符（带衰减）
        this.player.cancelQueue(this.audioContext);
        envelope.cancel();

        this.activeEnvelopes.delete(midi);
        keyElement.classList.remove('active');
    }

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
            this.volume = parseFloat(e.target.value);
            document.getElementById('volumeValue').textContent = `${Math.round(this.volume * 100)}%`;
        });
    }

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

    playMidi() {
        if (!this.midiData || this.isPlaying) return;

        this.isPlaying = true;
        document.getElementById('playMidi').disabled = true;

        const track = this.midiData.track[1] || this.midiData.track[0];
        const ticksPerBeat = this.midiData.timeDivision;
        const microsecondsPerBeat = 500000;
        const msPerTick = (microsecondsPerBeat / ticksPerBeat / 1000) / this.playbackSpeed;

        let currentTime = 0;

        track.event.forEach(event => {
            currentTime += event.deltaTime * msPerTick;

            if (event.type === 9 && event.data[1] > 0) {
                const timeout = setTimeout(() => {
                    const midi = event.data[0];
                    const velocity = event.data[1] / 127 * this.volume;

                    // 播放音符
                    this.player.queueWaveTable(
                        this.audioContext,
                        this.audioContext.destination,
                        this.instrument,
                        this.audioContext.currentTime,
                        midi,
                        9999,
                        velocity
                    );

                    const keyElement = document.querySelector(`[data-midi="${midi}"]`);
                    if (keyElement) {
                        keyElement.classList.add('active');
                    }
                }, currentTime);

                this.midiTimeouts.push(timeout);
            } else if (event.type === 8 || (event.type === 9 && event.data[1] === 0)) {
                const timeout = setTimeout(() => {
                    const midi = event.data[0];

                    const keyElement = document.querySelector(`[data-midi="${midi}"]`);
                    if (keyElement) {
                        keyElement.classList.remove('active');
                    }
                }, currentTime);

                this.midiTimeouts.push(timeout);
            }
        });

        const finalTimeout = setTimeout(() => {
            this.stopMidi();
        }, currentTime + 1000);

        this.midiTimeouts.push(finalTimeout);
    }

    stopMidi() {
        this.midiTimeouts.forEach(timeout => clearTimeout(timeout));
        this.midiTimeouts = [];
        this.player.cancelQueue(this.audioContext);

        document.querySelectorAll('.key.active').forEach(key => {
            key.classList.remove('active');
        });

        this.activeEnvelopes.clear();
        this.isPlaying = false;
        document.getElementById('playMidi').disabled = false;
    }

    initKeyboard() {
        const keyMap = {
            'a': 48, 'w': 49, 's': 50, 'e': 51, 'd': 52,
            'f': 53, 't': 54, 'g': 55, 'y': 56, 'h': 57,
            'u': 58, 'j': 59, 'k': 60, 'o': 61, 'l': 62
        };

        document.addEventListener('keydown', (e) => {
            const midi = keyMap[e.key.toLowerCase()];
            if (midi && !e.repeat) {
                const keyElement = document.querySelector(`[data-midi="${midi}"]`);
                if (keyElement) {
                    this.playNote(midi, keyElement.dataset.note, keyElement);
                }
            }
        });

        document.addEventListener('keyup', (e) => {
            const midi = keyMap[e.key.toLowerCase()];
            if (midi) {
                const keyElement = document.querySelector(`[data-midi="${midi}"]`);
                if (keyElement) {
                    this.stopNote(midi, keyElement);
                }
            }
        });
    }
}

window.addEventListener('DOMContentLoaded', () => {
    new Piano();
});
