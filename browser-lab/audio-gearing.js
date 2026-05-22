/**
 * Aurion audio gearing — tight-Q population curves for popular music.
 * Maps raw psychoacoustic features → visual matrix with high resolution
 * inside typical song norms and dramatic response only at meaningful tails.
 */
(function (global) {
    'use strict';

    const SYMMETRIES = [4, 6, 8, 10, 12, 16, 24];

    /** Population priors (centers in natural units, sigma = tight Q width). */
    const MUSIC_PRIORS = {
        durationSec: { center: 210, sigma: 45, q: 2.4 },       // ~3:30 pop single
        tempoBpm: { center: 118, sigma: 22, q: 2.2 },          // mainstream pop/rock
        avgRms: { center: 0.14, sigma: 0.045, q: 2.6 },        // streaming loudness band
        avgZcr: { center: 72, sigma: 28, q: 2.0 },
        crestFactor: { center: 2.35, sigma: 0.55, q: 2.3 },
        stereoWidth: { center: 0.55, sigma: 0.35, q: 2.1 },
        dynamicRangeDb: { center: 9.5, sigma: 3.5, q: 2.4 },
        spectralCentroid: { center: 2200, sigma: 900, q: 2.0 },
        spectralRolloff: { center: 4800, sigma: 2200, q: 2.0 },
        spectralFlatness: { center: 0.12, sigma: 0.08, q: 2.5 },
        phaseCoherence: { center: 0.55, sigma: 0.28, q: 2.2 },
        peakDensity: { center: 0.08, sigma: 0.05, q: 2.3 },
        lowEnergy: { center: 0.28, sigma: 0.12, q: 2.2 },
        midEnergy: { center: 0.48, sigma: 0.14, q: 2.2 },
        highEnergy: { center: 0.24, sigma: 0.11, q: 2.2 },
    };

    /** Inferred genre/subgenre weights from features (no external metadata required). */
    const GENRE_SIGNATURES = {
        pop: { centroid: 2400, flatness: 0.08, zcr: 85, crest: 2.2, tempo: 115, high: 0.22 },
        hiphop: { centroid: 900, flatness: 0.05, zcr: 55, crest: 2.8, tempo: 92, low: 0.42 },
        edm: { centroid: 3200, flatness: 0.15, zcr: 110, crest: 2.0, tempo: 128, high: 0.35 },
        rock: { centroid: 2800, flatness: 0.06, zcr: 95, crest: 2.6, tempo: 122, mid: 0.52 },
        ambient: { centroid: 1400, flatness: 0.22, zcr: 45, crest: 1.8, tempo: 72, low: 0.35 },
        classical: { centroid: 1800, flatness: 0.04, zcr: 60, crest: 3.2, tempo: 96, dynamic: 16 },
        metal: { centroid: 3400, flatness: 0.04, zcr: 120, crest: 3.0, tempo: 138, high: 0.30 },
        rnb: { centroid: 1900, flatness: 0.07, zcr: 70, crest: 2.1, tempo: 88, low: 0.38 },
    };

    /** Map free-text metadata Genre labels → canonical gearing keys. */
    const USER_GENRE_ALIASES = {
        pop: ['pop', 'dance pop', 'synthpop', 'k-pop', 'j-pop', 'top 40'],
        hiphop: ['hip hop', 'hip-hop', 'rap', 'trap', 'drill', 'grime'],
        edm: ['edm', 'electronic', 'house', 'techno', 'trance', 'dubstep'],
        rock: ['rock', 'alternative', 'indie', 'punk', 'grunge', 'alt-rock'],
        ambient: ['ambient', 'new age', 'drone', 'soundscape'],
        classical: ['classical', 'orchestral', 'chamber', 'baroque'],
        metal: ['metal', 'heavy metal', 'hardcore', 'death metal'],
        rnb: ['r&b', 'rnb', 'soul', 'neo soul', 'neo-soul'],
    };

    function normalizeUserGenre(label) {
        const text = String(label || '').toLowerCase().trim();
        if (!text) return null;
        for (const [key, aliases] of Object.entries(USER_GENRE_ALIASES)) {
            if (aliases.some((alias) => text.includes(alias))) return key;
        }
        return null;
    }

    function mergeUserGenreHints(inferred, userGenreKey) {
        if (!userGenreKey || !GENRE_SIGNATURES[userGenreKey]) return inferred;
        const merged = Object.assign({}, inferred);
        const boost = 0.35;
        merged[userGenreKey] = (merged[userGenreKey] || 0) + boost;
        let total = 0;
        for (const key of Object.keys(GENRE_SIGNATURES)) total += merged[key] || 0;
        if (total <= 0) return inferred;
        for (const key of Object.keys(GENRE_SIGNATURES)) merged[key] = (merged[key] || 0) / total;
        merged.dominant = Object.keys(GENRE_SIGNATURES).reduce((best, key) =>
            (merged[key] > merged[best] ? key : best), Object.keys(GENRE_SIGNATURES)[0]);
        merged.userGenre = userGenreKey;
        return merged;
    }

    function clamp(v, lo, hi) {
        return Math.max(lo, Math.min(hi, v));
    }

    function clamp01(v) {
        return clamp(v, 0, 1);
    }

    /**
     * Tight-Q normalized response: 0 at population center, approaches ±1 at tails.
     * q controls steepness — higher q = more resolution inside the typical band.
     */
    function gearDeviation(value, center, sigma, q) {
        const z = (value - center) / Math.max(sigma, 1e-9);
        return clamp(Math.tanh(z * q), -1, 1);
    }

    /** Map deviation [-1,1] to output range with optional asymmetric emphasis. */
    function gearMap(deviation, outMin, outMax, emphasis) {
        const u = (deviation * emphasis + 1) * 0.5;
        return outMin + clamp01(u) * (outMax - outMin);
    }

    /** Signed spread: center maps to mid-range; tails push toward extremes. */
    function gearSpread(value, prior, outMin, outMax, emphasis) {
        const d = gearDeviation(value, prior.center, prior.sigma, prior.q);
        return gearMap(d, outMin, outMax, emphasis);
    }

    function bandAboveSilence(energy, silenceFloor) {
        const ref = Math.max(silenceFloor, 1e-6);
        return clamp01((energy - ref) / Math.max(1 - ref, 1e-6));
    }

    function inferGenreHints(acoustic) {
        const hints = {};
        const tempo = acoustic.estimatedTempoBpm || MUSIC_PRIORS.tempoBpm.center;
        const centroid = acoustic.spectralCentroid || MUSIC_PRIORS.spectralCentroid.center;
        const flatness = acoustic.spectralFlatness ?? MUSIC_PRIORS.spectralFlatness.center;
        const zcr = acoustic.avgZcr || MUSIC_PRIORS.avgZcr.center;
        const crest = acoustic.crestFactor || MUSIC_PRIORS.crestFactor.center;
        const low = acoustic.lowEnergy ?? MUSIC_PRIORS.lowEnergy.center;
        const mid = acoustic.midEnergy ?? MUSIC_PRIORS.midEnergy.center;
        const high = acoustic.highEnergy ?? MUSIC_PRIORS.highEnergy.center;
        const dyn = acoustic.dynamicRangeDb || MUSIC_PRIORS.dynamicRangeDb.center;

        for (const [name, sig] of Object.entries(GENRE_SIGNATURES)) {
            let score = 0;
            if (sig.centroid != null) score += 1.2 - Math.abs(centroid - sig.centroid) / 4000;
            if (sig.flatness != null) score += 1.0 - Math.abs(flatness - sig.flatness) / 0.25;
            if (sig.zcr != null) score += 1.0 - Math.abs(zcr - sig.zcr) / 120;
            if (sig.crest != null) score += 0.8 - Math.abs(crest - sig.crest) / 2.5;
            if (sig.tempo != null) score += 1.1 - Math.abs(tempo - sig.tempo) / 80;
            if (sig.low != null) score += 0.7 - Math.abs(low - sig.low) / 0.5;
            if (sig.mid != null) score += 0.7 - Math.abs(mid - sig.mid) / 0.5;
            if (sig.high != null) score += 0.7 - Math.abs(high - sig.high) / 0.5;
            if (sig.dynamic != null) score += 0.9 - Math.abs(dyn - sig.dynamic) / 14;
            hints[name] = Math.max(0, score);
        }

        const total = Object.values(hints).reduce((a, b) => a + b, 0) || 1;
        for (const k of Object.keys(hints)) hints[k] /= total;
        hints.dominant = Object.entries(hints).sort((a, b) => b[1] - a[1])[0][0];
        return hints;
    }

    /**
     * Per-ring profile from frequency blocks relative to silence floor.
     * Inner rings ← low band, mid rings ← mid band, outer ← high band.
     */
    function deriveRingProfile(acoustic, hashBytes, ringCount) {
        const silence = acoustic.silenceFloorRms ?? 0.008;
        const low = bandAboveSilence(acoustic.lowEnergy ?? 0.33, silence * 8);
        const mid = bandAboveSilence(acoustic.midEnergy ?? 0.34, silence * 8);
        const high = bandAboveSilence(acoustic.highEnergy ?? 0.33, silence * 8);
        const bandSum = low + mid + high || 1;
        const norm = { low: low / bandSum, mid: mid / bandSum, high: high / bandSum };

        const profile = [];
        for (let i = 0; i < ringCount; i++) {
            const t = ringCount <= 1 ? 0.5 : i / (ringCount - 1);
            const lowW = Math.max(0, 1 - t * 2.2);
            const highW = Math.max(0, (t - 0.35) * 1.8);
            const midW = Math.max(0, 1 - Math.abs(t - 0.45) * 2.4);
            const weight = lowW * norm.low + midW * norm.mid + highW * norm.high;
            const hashN = hashBytes[(i + 3) % hashBytes.length] / 255;
            const symBias = Math.round((lowW * 4 + midW * 8 + highW * 12 + hashN * 4) - 2);
            const sharpBias = clamp01(midW * 0.35 + highW * 0.55 + lowW * 0.15);
            const warpBias = 0.88 + weight * 0.22 + hashN * 0.08;
            profile.push({
                index: i + 1,
                radialT: t,
                weight: clamp01(weight * 1.35),
                symBias,
                sharpBias,
                warpBias,
                bandMix: { low: lowW * norm.low, mid: midW * norm.mid, high: highW * norm.high },
            });
        }
        return profile;
    }

    function deriveRingCount(acoustic, hashBytes, genreHints) {
        const silence = acoustic.silenceFloorRms ?? 0.008;
        const low = bandAboveSilence(acoustic.lowEnergy ?? 0.33, silence * 8);
        const mid = bandAboveSilence(acoustic.midEnergy ?? 0.34, silence * 8);
        const high = bandAboveSilence(acoustic.highEnergy ?? 0.33, silence * 8);
        const bandSpread = 1 - Math.max(low, mid, high) / Math.max(low + mid + high, 1e-6);
        const rmsDev = gearDeviation(acoustic.avgRms || 0.14, MUSIC_PRIORS.avgRms.center, MUSIC_PRIORS.avgRms.sigma, MUSIC_PRIORS.avgRms.q);
        const dynDev = gearDeviation(acoustic.dynamicRangeDb || 9.5, MUSIC_PRIORS.dynamicRangeDb.center, MUSIC_PRIORS.dynamicRangeDb.sigma, MUSIC_PRIORS.dynamicRangeDb.q);
        const durDev = gearDeviation(acoustic.durationSec || 210, MUSIC_PRIORS.durationSec.center, MUSIC_PRIORS.durationSec.sigma, MUSIC_PRIORS.durationSec.q);
        const genreSpread = 1 - (genreHints[genreHints.dominant] || 0.25);

        const composite =
            bandSpread * 0.38 +
            ((rmsDev + 1) * 0.5) * 0.22 +
            ((dynDev + 1) * 0.5) * 0.18 +
            ((durDev + 1) * 0.5) * 0.12 +
            genreSpread * 0.10;

        const hashNudge = (hashBytes[11] % 5) - 2;
        return clamp(Math.round(3 + composite * 8 + hashNudge), 3, 11);
    }

    function pickSymmetry(acoustic, hashBytes, genreHints) {
        const zcrDev = gearDeviation(acoustic.avgZcr || 72, MUSIC_PRIORS.avgZcr.center, MUSIC_PRIORS.avgZcr.sigma, MUSIC_PRIORS.avgZcr.q);
        const peakDev = gearDeviation(acoustic.peakDensity || 0.08, MUSIC_PRIORS.peakDensity.center, MUSIC_PRIORS.peakDensity.sigma, MUSIC_PRIORS.peakDensity.q);
        const genreIdx = {
            pop: 8, hiphop: 6, edm: 12, rock: 8, ambient: 4, classical: 6, metal: 16, rnb: 6,
        };
        const genreSym = genreIdx[genreHints.dominant] || 8;
        const acousticSym = acoustic.symmetry;
        let baseIdx = SYMMETRIES.indexOf(acousticSym);
        if (baseIdx < 0) {
            baseIdx = clamp(Math.round(2 + ((zcrDev + 1) * 0.5) * 4 + peakDev * 1.5), 0, SYMMETRIES.length - 1);
        }
        const genreTarget = SYMMETRIES.indexOf(genreSym);
        const blended = clamp(Math.round(baseIdx * 0.55 + genreTarget * 0.45), 0, SYMMETRIES.length - 1);
        const symNudge = (hashBytes[8] % 3) - 1;
        return SYMMETRIES[clamp(blended + symNudge, 0, SYMMETRIES.length - 1)];
    }

    function buildGearedCosmicMatrix(hashBytes, acousticData, preset, helpers) {
        const hashUnit = helpers.hashUnit;
        const seedSlice = Array.from(hashBytes).map(b => b.toString(16).padStart(2, '0')).join('');
        const genreHints = mergeUserGenreHints(
            inferGenreHints(acousticData),
            normalizeUserGenre(helpers.userGenre)
        );
        const rings = deriveRingCount(acousticData, hashBytes, genreHints);
        const ringProfile = deriveRingProfile(acousticData, hashBytes, rings);
        const sym = pickSymmetry(acousticData, hashBytes, genreHints);

        const crestDev = gearDeviation(acousticData.crestFactor || 2.35, MUSIC_PRIORS.crestFactor.center, MUSIC_PRIORS.crestFactor.sigma, MUSIC_PRIORS.crestFactor.q);
        const lineEnergy = gearMap(crestDev, 0.75, 2.65, 1.15);

        const highDev = gearDeviation(acousticData.highEnergy ?? 0.24, MUSIC_PRIORS.highEnergy.center, MUSIC_PRIORS.highEnergy.sigma, MUSIC_PRIORS.highEnergy.q);
        const peakDev = gearDeviation(acousticData.peakDensity || 0.08, MUSIC_PRIORS.peakDensity.center, MUSIC_PRIORS.peakDensity.sigma, MUSIC_PRIORS.peakDensity.q);
        const flux = clamp01(0.12 + ((highDev + 1) * 0.5) * 0.55 + ((peakDev + 1) * 0.5) * 0.38);

        const flatDev = gearDeviation(acousticData.spectralFlatness ?? 0.12, MUSIC_PRIORS.spectralFlatness.center, MUSIC_PRIORS.spectralFlatness.sigma, MUSIC_PRIORS.spectralFlatness.q);
        const dualF = clamp01(0.05 + ((crestDev + 1) * 0.5) * 0.35 + ((flatDev + 1) * 0.5) * 0.45);
        const sharp = gearSpread(acousticData.spectralFlatness ?? 0.12, MUSIC_PRIORS.spectralFlatness, 0.35, 1.95, 1.2);
        const sharpInv = 2.0 - sharp;

        const phaseDev = gearDeviation(acousticData.phaseCoherence ?? 0.55, MUSIC_PRIORS.phaseCoherence.center, MUSIC_PRIORS.phaseCoherence.sigma, MUSIC_PRIORS.phaseCoherence.q);
        const asym = clamp01(0.08 + ((crestDev + 1) * 0.5) * 0.42 + ((1 - ((phaseDev + 1) * 0.5)) * 0.55));

        const stereoDev = gearDeviation(acousticData.stereoWidth || 0.55, MUSIC_PRIORS.stereoWidth.center, MUSIC_PRIORS.stereoWidth.sigma, MUSIC_PRIORS.stereoWidth.q);
        const stereo = clamp01(0.2 + ((stereoDev + 1) * 0.5) * 0.75);

        const dynDev = gearDeviation(acousticData.dynamicRangeDb || 9.5, MUSIC_PRIORS.dynamicRangeDb.center, MUSIC_PRIORS.dynamicRangeDb.sigma, MUSIC_PRIORS.dynamicRangeDb.q);
        const anchorIndex = clamp(Math.round(3 - dynDev * 1.8 + ((hashBytes[10] % 3) - 1)), 1, 5);

        const durDev = gearDeviation(acousticData.durationSec || 210, MUSIC_PRIORS.durationSec.center, MUSIC_PRIORS.durationSec.sigma, MUSIC_PRIORS.durationSec.q);
        const plasmaFeature = clamp01(0.25 + ((phaseDev + 1) * 0.5) * 0.45 + durDev * 0.08);

        const hueShift = Math.floor(hashUnit(hashBytes, 12) * 360);
        const rotationOffset = hashUnit(hashBytes, 13) * Math.PI * 2;
        const spiral = gearMap(
            gearDeviation(acousticData.estimatedTempoBpm || 118, MUSIC_PRIORS.tempoBpm.center, MUSIC_PRIORS.tempoBpm.sigma, MUSIC_PRIORS.tempoBpm.q),
            -0.55, 0.55, 1.0
        ) + (hashUnit(hashBytes, 14) - 0.5) * 0.25;
        const layerWarp = 0.88 + hashUnit(hashBytes, 15) * 0.22 + ((dynDev + 1) * 0.5) * 0.08;
        const petalJitter = clamp01(0.15 + bandSpreadFromBands(acousticData) * 0.65 + hashUnit(hashBytes, 16) * 0.25);
        const densityBoost = clamp01(0.1 + flux * 0.55 + hashUnit(hashBytes, 17) * 0.35);
        const signatureTwist = hashUnit(hashBytes, 18) * Math.PI * 2;

        return {
            seedStr: seedSlice,
            sym,
            anchorIndex,
            rings,
            ringProfile,
            lineEnergy,
            flux,
            dualF,
            sharp: sharpInv,
            asym,
            stereo,
            hueShift,
            rotationOffset,
            spiral,
            layerWarp,
            petalJitter,
            densityBoost,
            signatureTwist,
            plasmaFeature,
            gearing: {
                genreHints,
                durationDev: durDev,
                tempoDev: gearDeviation(acousticData.estimatedTempoBpm || 118, MUSIC_PRIORS.tempoBpm.center, MUSIC_PRIORS.tempoBpm.sigma, MUSIC_PRIORS.tempoBpm.q),
                rmsDev: gearDeviation(acousticData.avgRms || 0.14, MUSIC_PRIORS.avgRms.center, MUSIC_PRIORS.avgRms.sigma, MUSIC_PRIORS.avgRms.q),
            },
        };
    }

    function bandSpreadFromBands(acoustic) {
        const low = acoustic.lowEnergy ?? 0.33;
        const mid = acoustic.midEnergy ?? 0.34;
        const high = acoustic.highEnergy ?? 0.33;
        const m = Math.max(low, mid, high);
        return 1 - m / Math.max(low + mid + high, 1e-6);
    }

    // --- Art Directive v1 (browser parity with Python aurion_art_directive) ---
    const KNOWN_LAYERS = [
        "base_void", "cymatic_field", "mandala_shells", "filament_weave",
        "plasma_glow", "orbit_filigree", "starfield", "yantra_seal",
        "energy_overlay", "hash_signature", "wave_ripples"
    ];

    const ARCHETYPE_CATALOG = {
        crystalline_harmonic_bloom: { name: "Crystalline Harmonic Bloom", symMin: 8, asymMax: 0.35, fluxMax: 0.45, stereoMax: 0.6 },
        nebular_filament_storm: { name: "Nebular Filament Storm", symMin: 6, asymMin: 0.4, fluxMin: 0.6 },
        stairway_ascendant_spires: { name: "Stairway Ascendant Spires", spiralMin: 0.2, ringsMin: 7, stereoMin: 0.5 },
        highway_infernal_grid: { name: "Highway Infernal Grid", asymMin: 0.35, fluxMin: 0.55, anchorMin: 4 },
        billie_jean_mirror_pulse: { name: "Billie Jean Mirror Pulse", symMin: 8, stereoMin: 0.6, sharpMin: 1.2 },
        cosmic_ribbon_weave: { name: "Cosmic Ribbon Weave", dualFMin: 0.4, ringsMin: 6, petalJitterMin: 0.3 },
        plasma_cymatic_resonance: { name: "Plasma Cymatic Resonance", fluxMin: 0.5, phaseMin: 0.3 },
        void_lace_orbit: { name: "Void Lace Orbit Trap", fluxMax: 0.4, densityMax: 0.55 },
    };

    function _inferArchetypeJS(matrix) {
        const sym = matrix.sym || 8;
        const asym = matrix.asym || 0.2;
        const flux = matrix.flux || 0.3;
        const stereo = matrix.stereo || 0.4;
        const spiral = matrix.spiral || 0.0;
        const rings = matrix.rings || 6;
        const sharp = matrix.sharp || 1.0;
        const dualF = matrix.dualF || 0.2;
        const petalJitter = matrix.petalJitter || 0.2;
        const anchor = matrix.anchorIndex || 3;
        const density = matrix.densityBoost || 0.3;
        const phase = (matrix.gearing && matrix.gearing.phaseCoherence) || 0.5;

        let bestKey = "crystalline_harmonic_bloom";
        let bestScore = -1;
        Object.keys(ARCHETYPE_CATALOG).forEach(function (key) {
            const spec = ARCHETYPE_CATALOG[key];
            let s = 0;
            if (spec.symMin && sym >= spec.symMin) s += 1.0;
            if (spec.asymMin && asym >= spec.asymMin) s += 1.0;
            if (spec.asymMax && asym <= spec.asymMax) s += 1.0;
            if (spec.fluxMin && flux >= spec.fluxMin) s += 1.2;
            if (spec.fluxMax && flux <= spec.fluxMax) s += 0.8;
            if (spec.stereoMin && stereo >= spec.stereoMin) s += 0.9;
            if (spec.stereoMax && stereo <= spec.stereoMax) s += 0.7;
            if (spec.spiralMin && spiral >= spec.spiralMin) s += 1.1;
            if (spec.ringsMin && rings >= spec.ringsMin) s += 0.8;
            if (spec.sharpMin && sharp >= spec.sharpMin) s += 0.7;
            if (spec.dualFMin && dualF >= spec.dualFMin) s += 0.9;
            if (spec.petalJitterMin && petalJitter >= spec.petalJitterMin) s += 0.6;
            if (spec.anchorMin && anchor >= spec.anchorMin) s += 0.5;
            if (key === "plasma_cymatic_resonance" && phase > 0.25) s += 1.0;
            if (key === "void_lace_orbit" && flux < 0.45 && density < 0.55) s += 0.8;
            if (s > bestScore) { bestScore = s; bestKey = key; }
        });
        return ARCHETYPE_CATALOG[bestKey].name;
    }

    function _choosePaletteJS(matrix) {
        const hue = matrix.hueShift || 240;
        const stereo = matrix.stereo || 0.4;
        const flux = matrix.flux || 0.3;
        const dom = (matrix.gearing && matrix.gearing.genreHints && matrix.gearing.genreHints.dominant) || "pop";
        if (dom === "metal" || dom === "edm" || flux > 0.7) return "infernal_plasma_crimson_orange";
        if (dom === "ambient" || dom === "classical" || flux < 0.25) return "ethereal_ice_cyan_violet";
        if (stereo > 0.65) return "neon_cosmic_gold_cyan_magenta";
        if (hue < 60 || hue > 300) return "byzantine_gold_ruby";
        return "cosmic_teal_gold_midnight";
    }

    function _selectLayersJS(archetype, matrix) {
        const flux = matrix.flux || 0.3;
        const asym = matrix.asym || 0.2;
        const rings = matrix.rings || 6;
        const density = matrix.densityBoost || 0.3;
        const stereo = matrix.stereo || 0.4;
        const layers = ["base_void", "cymatic_field", "mandala_shells"];
        if (flux > 0.35 || /filament|storm/i.test(archetype)) layers.push("filament_weave");
        if (flux > 0.25 || density > 0.4) layers.push("plasma_glow");
        if (asym > 0.25 || /lace|orbit/i.test(archetype)) layers.push("orbit_filigree");
        layers.push("starfield");
        layers.push("yantra_seal");
        if (stereo > 0.5 || /energy|pulse/i.test(archetype)) layers.push("energy_overlay");
        layers.push("hash_signature");
        if (rings >= 7 || /wave|ribbon/i.test(archetype)) layers.push("wave_ripples");
        const seen = {}; const ordered = [];
        layers.forEach(function (l) { if (!seen[l]) { seen[l] = true; ordered.push(l); } });
        return ordered;
    }

    function toArtDirective(hashBytes, acousticData, preset, userGenre) {
        // Re-use the exact same geared matrix the rest of the lab uses
        const matrix = buildGearedCosmicMatrix(hashBytes, acousticData, preset || "cosmic", userGenre || null);

        const petalDensity = Math.max(0, Math.min(1, 0.35 + (matrix.rings - 3) / 8 * 0.45 + (matrix.petalJitter || 0) * 0.25));
        const spiralTension = Math.max(-0.6, Math.min(0.6, ((matrix.spiral || 0) * 0.9 + 0.5) * (matrix.spiral >= 0 ? 1 : -1) * 0.6));

        const archetype = _inferArchetypeJS(matrix);
        const palette = _choosePaletteJS(matrix);
        const layers = _selectLayersJS(archetype, matrix);

        // 6-bit hexagram (simple stable fold, matches Python logic)
        const z = (acousticData.avgZcr || 70) & 0xF;
        const r = Math.floor((acousticData.avgRms || 0.14) * 100) & 0x7;
        const hb0 = (hashBytes && hashBytes.length ? hashBytes[0] : 0) & 0x3;
        const p = Math.floor((acousticData.peakDensity || 0.08) * 200) & 0x3;
        const s = Math.floor((acousticData.spectralCentroid || 2200) / 100) & 0x7;
        const hexagram = (z ^ (r << 1) ^ (hb0 << 3) ^ (p << 4) ^ (s << 5)) & 0x3F;

        const fullHash = Array.prototype.map.call(hashBytes || [], function (b) { return ("0" + b.toString(16)).slice(-2); }).join("");
        const seed = fullHash.slice(0, 16) || "0000000000000000";

        return {
            schema_version: "aurion-art-directive-v1",
            source_audio_sha256: fullHash,
            seed: seed,
            archetype: archetype,
            hexagram: hexagram,
            geometry: {
                symmetry: matrix.sym,
                rings: matrix.rings,
                petal_density: Math.round(petalDensity * 1000) / 1000,
                spiral_tension: Math.round(spiralTension * 1000) / 1000,
                cymatic_nodes: [], // populated server-side or via richer JS later
                anchor: matrix.anchorIndex,
                asym: Math.round(matrix.asym * 1000) / 1000,
                flux: Math.round(matrix.flux * 1000) / 1000,
                raw_matrix: matrix,
            },
            color: {
                palette: palette,
                primary_hue: matrix.hueShift,
                energy_bias: Math.round((0.4 + matrix.flux * 0.5) * 1000) / 1000,
                darkness: Math.round((0.78 + (1 - (matrix.densityBoost || 0.3)) * 0.15) * 1000) / 1000,
                stereo_split: Math.round(((matrix.stereo || 0.5) - 0.5) * 1.6 * 1000) / 1000,
            },
            layers: layers,
            render_targets: {
                browser_preview: { max_size: 1600, simplify_particles: true, realtime: true },
                sangraha_final: { size: 8192, supersample: 2, full_detail: true },
            },
            meta: {
                acoustic_summary: {
                    durationSec: acousticData.durationSec,
                    estimatedTempoBpm: acousticData.estimatedTempoBpm,
                    dominantGenre: matrix.gearing && matrix.gearing.genreHints && matrix.gearing.genreHints.dominant,
                },
                gearing: matrix.gearing || {},
                engine: "aurion-art-directive-extractor-v1-js",
            },
        };
    }

    global.AurionAudioGearing = {
        MUSIC_PRIORS,
        GENRE_SIGNATURES,
        USER_GENRE_ALIASES,
        SYMMETRIES,
        gearDeviation,
        gearSpread,
        inferGenreHints,
        normalizeUserGenre,
        mergeUserGenreHints,
        deriveRingProfile,
        deriveRingCount,
        buildGearedCosmicMatrix,
        toArtDirective,                 // NEW: emits the canonical aurion-art-directive-v1 contract
    };
})(typeof window !== 'undefined' ? window : globalThis);
