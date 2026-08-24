using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.SceneManagement;
using UnityEngine.UI;
#if UNITY_EDITOR
using UnityEditor;
#endif

namespace EndfieldGraphShaderLab
{
    public sealed class CharacterRecoveryViewerUI : MonoBehaviour
    {
        private const string InitialModelEnvironment =
            "ENDFIELD_CHARACTER_RECOVERY_INITIAL_MODEL";
        private readonly List<CharacterRecoveryRig> rigs = new List<CharacterRecoveryRig>();
        private readonly List<ModelEntry> models = new List<ModelEntry>();
        private readonly List<ClipEntry> allClips = new List<ClipEntry>();
        private readonly List<ClipEntry> visibleClips = new List<ClipEntry>();
        private readonly List<ClipEntry> helperClips = new List<ClipEntry>();
        private readonly List<RecoveredStateEntry> recoveredStates = new List<RecoveredStateEntry>();
        private readonly List<RecoveredStateEntry> visibleRecoveredStates = new List<RecoveredStateEntry>();
        private readonly List<RecoveredLayerEntry> activeRecoveredLayers = new List<RecoveredLayerEntry>();
        private readonly List<StateTransitionEntry> stateTransitions = new List<StateTransitionEntry>();
        private readonly List<StateButtonEntry> stateButtons = new List<StateButtonEntry>();
        private readonly List<string> clipNames = new List<string>();
        private readonly List<string> helperClipNames = new List<string>();
        private readonly List<string> clipCategoryOptions = new List<string>();

        private Dropdown modelDropdown;
        private Dropdown clipModeDropdown;
        private Dropdown clipCategoryDropdown;
        private Dropdown clipDropdown;
        private Dropdown helperDropdown;
        private Dropdown resolutionDropdown;
        private InputField clipSearchInput;
        private Button playPauseButton;
        private Button restartButton;
        private Button frameButton;
        private Button resetCameraButton;
        private Toggle loopToggle;
        private Toggle poseToggle;
        private Slider speedSlider;
        private Slider timeSlider;
        private Slider poseWeightSlider;
        private Image clipDropdownProgressFill;
        private Text playPauseText;
        private Text speedText;
        private Text timeText;
        private Text poseWeightText;
        private Text clipFilterSummaryText;
        private Text statusText;
        private Text stateTransitionStatusText;
        private Transform stateTransitionContent;
        private Font runtimeUiFont;

        private CharacterRecoveryRig activeRig;
        private ModelEntry activeModel;
        private Animation activeAnimation;
        private CharacterProceduralIk activePoseCorrection;
        private string activeClipName = "";
        private string activeHelperClipName = "";
        private string activeRecoveredStateLabel = "";
        private RecoveredStateEntry activeRecoveredState;
        private string activeLogicalState = "";
        private string selectedClipCategory = "";
        private string clipSearchQuery = "";
        private ClipMode clipMode = ClipMode.Primary;
        private bool playing;
        private bool updatingUi;
        private bool draggingTime;
        private bool selectingInitialClip;
        private Coroutine stateTransitionCoroutine;
        private int stateTransitionGeneration;
        private bool playingStateTransitionClip;
        private bool playingStateGraphLoop;
        private bool keepAllModelsResident;
        private float residentHorizontalSpacing = 3.5f;

        private enum ClipMode
        {
            Primary,
            RecoveredState,
            Helper,
            All,
        }

        private sealed class ClipEntry
        {
            public string Name = "";
            public string ClipClass = "";
            public string ClipCategory = "";
            public string LayerRole = "";
            public bool StandaloneCandidate;
            public bool HelperOrAdditive;
            public string WidgetPropPath = "";
            public string AutoHelperClip = "";
            public string CombinationNote = "";
            public string Note = "";
            public string SearchText = "";
        }

        private sealed class RecoveredLayerEntry
        {
            public string Clip = "";
            public int Layer = 1;
            public bool Additive = true;
            public float Weight = 1f;
            public string Role = "";
            public bool UseControllerLoop;
            public bool ControllerLoop;
        }

        private sealed class RecoveredStateEntry
        {
            public string Label = "";
            public string BaseClip = "";
            public string Source = "";
            public string Confidence = "";
            public string Note = "";
            public string ClipCategory = "recovered";
            public string SearchText = "";
            public readonly List<string> EvidenceClips = new List<string>();
            public readonly List<string> VisibleProps = new List<string>();
            public readonly List<RecoveredLayerEntry> Layers = new List<RecoveredLayerEntry>();
        }

        private sealed class StateTransitionEntry
        {
            public string FromState = "";
            public string ToState = "";
            public string TransitionClip = "";
            public string LoopClip = "";
        }

        private sealed class StateButtonEntry
        {
            public string State = "";
            public string LoopClip = "";
            public Button Button;
        }

        private sealed class ModelEntry
        {
            public string DisplayName = "";
            public string RootName = "";
            public string PrefabAssetPath = "";
            public GameObject Prefab;
            public CharacterRecoveryPresentationProfile PresentationProfile;
            public Transform SpawnParent;
            public CharacterRecoveryRig Rig;
            public bool RuntimeInstance;
            public CharacterLocalPoseSnapshot ReferencePose;

            public bool IsLoaded => Rig != null;
        }

        private static readonly Vector2Int[] ResolutionOptions =
        {
            new Vector2Int(1280, 720),
            new Vector2Int(1920, 1080),
            new Vector2Int(2560, 1440),
            new Vector2Int(3840, 2160),
        };

        private void Awake()
        {
            EnsureEventSystem();
            BuildUi();
        }

        private void Start()
        {
            RefreshModels();
        }

        private void Update()
        {
            HandleKeyboard();
            UpdateTimeUi();
        }

        /// <summary>
        /// Returns the viewer's explicit resident-lineup selection. This is
        /// the lab carrier for the original HGVFXManager player-center
        /// Transform; it deliberately refuses first/nearest-rig guesses.
        /// </summary>
        public static bool TryGetSelectedActorRoot(out Transform actorRoot)
        {
            actorRoot = null;
            CharacterRecoveryViewerUI[] viewers =
                FindObjectsOfType<CharacterRecoveryViewerUI>(true);
            for (int i = 0; i < viewers.Length; i++)
            {
                CharacterRecoveryViewerUI viewer = viewers[i];
                if (viewer == null ||
                    !viewer.isActiveAndEnabled ||
                    viewer.activeRig == null ||
                    !viewer.activeRig.gameObject.activeInHierarchy)
                {
                    continue;
                }

                Transform candidate = viewer.activeRig.transform;
                if (actorRoot != null && actorRoot != candidate)
                    return false;
                actorRoot = candidate;
            }
            return actorRoot != null;
        }

        public void RefreshModels()
        {
            rigs.Clear();
            models.Clear();
            keepAllModelsResident = false;
            residentHorizontalSpacing = 3.5f;
            foreach (CharacterRecoveryRig rig in FindObjectsOfType<CharacterRecoveryRig>(true))
            {
                if (!rig.gameObject.scene.IsValid())
                    continue;
                rigs.Add(rig);
                AddLoadedModel(rig);
            }

            if (rigs.Count == 0)
            {
                foreach (Animation animation in FindObjectsOfType<Animation>(true))
                {
                    if (!animation.gameObject.scene.IsValid())
                        continue;
                    var rig = animation.GetComponent<CharacterRecoveryRig>();
                    if (rig == null)
                        rig = animation.gameObject.AddComponent<CharacterRecoveryRig>();
                    rig.displayName = animation.gameObject.name;
                    rig.animationSource = animation;
                    rigs.Add(rig);
                    AddLoadedModel(rig);
                }
            }

            rigs.Sort(CompareRigs);
            AddCatalogModels();
            models.Sort(CompareModelEntries);
            EnsureResidentLineupLoaded();

            updatingUi = true;
            modelDropdown.ClearOptions();
            var options = new List<string>();
            foreach (ModelEntry model in models)
                options.Add(ModelDisplayName(model));
            modelDropdown.AddOptions(options);
            modelDropdown.interactable = models.Count > 1;
            updatingUi = false;

            int initialIndex = models.Count > 0 ? 0 : -1;
            string requestedInitialModel =
                Environment.GetEnvironmentVariable(InitialModelEnvironment);
            if (!string.IsNullOrWhiteSpace(requestedInitialModel))
            {
                int requestedIndex = models.FindIndex(model =>
                    string.Equals(model.RootName, requestedInitialModel,
                        StringComparison.OrdinalIgnoreCase));
                if (requestedIndex >= 0)
                    initialIndex = requestedIndex;
                else
                    Debug.LogWarning("Requested initial character recovery model is unavailable: " +
                        requestedInitialModel);
            }
            SelectModel(initialIndex);
        }

        private static int CompareRigs(CharacterRecoveryRig left, CharacterRecoveryRig right)
        {
            if (left == null || right == null)
                return left == null ? (right == null ? 0 : 1) : -1;
            int activeCompare = right.gameObject.activeSelf.CompareTo(left.gameObject.activeSelf);
            if (activeCompare != 0)
                return activeCompare;
            string leftName = string.IsNullOrEmpty(left.displayName) ? left.gameObject.name : left.displayName;
            string rightName = string.IsNullOrEmpty(right.displayName) ? right.gameObject.name : right.displayName;
            return string.CompareOrdinal(leftName, rightName);
        }

        private void AddLoadedModel(CharacterRecoveryRig rig)
        {
            if (rig == null)
                return;
            foreach (ModelEntry existingModel in models)
            {
                if (existingModel.Rig == rig)
                    return;
            }
            var model = new ModelEntry
            {
                DisplayName = string.IsNullOrEmpty(rig.displayName) ? rig.gameObject.name : rig.displayName,
                RootName = rig.gameObject.name,
                Rig = rig,
                SpawnParent = rig.transform.parent,
            };
            CaptureReferencePose(model, rig);
            models.Add(model);
        }

        private static void CaptureReferencePose(ModelEntry model, CharacterRecoveryRig rig)
        {
            if (model == null || rig == null)
                return;
            if (model.ReferencePose != null && model.ReferencePose.Count > 0)
                return;
            CharacterAnimationReferencePose provider =
                rig.GetComponent<CharacterAnimationReferencePose>();
            model.ReferencePose = provider != null
                ? provider.Snapshot
                : CharacterLocalPoseSnapshot.Capture(rig.transform);
        }

        private void RestoreActiveReferencePose()
        {
            CharacterLocalPoseSnapshot pose = activeModel != null ? activeModel.ReferencePose : null;
            pose?.Restore();
        }

        private void AddCatalogModels()
        {
            foreach (CharacterRecoveryActorCatalog catalog in FindObjectsOfType<CharacterRecoveryActorCatalog>(true))
            {
                if (catalog == null || catalog.entries == null || !catalog.gameObject.scene.IsValid())
                    continue;

                if (catalog.keepAllModelsResident && catalog.entries.Length > 0)
                {
                    keepAllModelsResident = true;
                    residentHorizontalSpacing = Mathf.Max(1f, catalog.horizontalSpacing);
                }

                Transform parent = catalog.SpawnParent;
                foreach (CharacterRecoveryActorCatalogEntry entry in catalog.entries)
                {
                    if (entry == null ||
                        (entry.prefab == null && string.IsNullOrEmpty(entry.prefabAssetPath)))
                        continue;
                    ModelEntry existing = FindModelEntry(
                        entry.displayName,
                        entry.rootName,
                        entry.prefabAssetPath);
                    if (existing != null)
                    {
                        existing.Prefab = entry.prefab;
                        existing.PresentationProfile = entry.presentationProfile;
                        existing.PrefabAssetPath = entry.prefabAssetPath;
                        existing.SpawnParent = parent;
                        continue;
                    }
                    models.Add(new ModelEntry
                    {
                        DisplayName = string.IsNullOrEmpty(entry.displayName) ? entry.rootName : entry.displayName,
                        RootName = entry.rootName,
                        PrefabAssetPath = entry.prefabAssetPath,
                        Prefab = entry.prefab,
                        PresentationProfile = entry.presentationProfile,
                        SpawnParent = parent,
                    });
                }
            }
        }

        private void EnsureResidentLineupLoaded()
        {
            if (!keepAllModelsResident || models.Count == 0)
                return;

            for (int index = 0; index < models.Count; index++)
            {
                ModelEntry model = models[index];
                CharacterRecoveryRig rig = EnsureModelLoaded(model);
                if (rig == null)
                    continue;
                rig.gameObject.SetActive(true);
                Transform root = rig.transform;
                root.localPosition = new Vector3(
                    (index - (models.Count - 1) * 0.5f) * residentHorizontalSpacing,
                    0f,
                    0f);
                root.SetSiblingIndex(index);
            }
        }

        private ModelEntry FindModelEntry(
            string displayName,
            string rootName,
            string prefabAssetPath)
        {
            foreach (ModelEntry model in models)
            {
                if (!string.IsNullOrEmpty(prefabAssetPath)
                    && string.Equals(model.PrefabAssetPath, prefabAssetPath, StringComparison.OrdinalIgnoreCase))
                    return model;
                if (!string.IsNullOrEmpty(rootName)
                    && string.Equals(model.RootName, rootName, StringComparison.OrdinalIgnoreCase))
                    return model;
                if (!string.IsNullOrEmpty(displayName)
                    && string.Equals(model.DisplayName, displayName, StringComparison.OrdinalIgnoreCase))
                    return model;
            }
            return null;
        }

        private static int CompareModelEntries(ModelEntry left, ModelEntry right)
        {
            if (left == null || right == null)
                return left == null ? (right == null ? 0 : 1) : -1;
            int activeCompare = ModelIsActive(right).CompareTo(ModelIsActive(left));
            if (activeCompare != 0)
                return activeCompare;
            int loadedCompare = right.IsLoaded.CompareTo(left.IsLoaded);
            if (loadedCompare != 0)
                return loadedCompare;
            return string.CompareOrdinal(ModelDisplayName(left), ModelDisplayName(right));
        }

        private static bool ModelIsActive(ModelEntry model)
        {
            return model != null && model.Rig != null && model.Rig.gameObject.activeSelf;
        }

        private static string ModelDisplayName(ModelEntry model)
        {
            if (model == null)
                return "<missing>";
            if (!string.IsNullOrEmpty(model.DisplayName))
                return model.DisplayName;
            if (!string.IsNullOrEmpty(model.RootName))
                return model.RootName;
            return string.IsNullOrEmpty(model.PrefabAssetPath) ? "<missing>" : model.PrefabAssetPath;
        }

        private static int CompareClipEntries(ClipEntry left, ClipEntry right)
        {
            if (left == null || right == null)
                return left == null ? (right == null ? 0 : 1) : -1;
            int helperCompare = left.HelperOrAdditive.CompareTo(right.HelperOrAdditive);
            if (helperCompare != 0)
                return helperCompare;
            int categoryCompare = ClipCategoryPriority(left.ClipCategory).CompareTo(ClipCategoryPriority(right.ClipCategory));
            if (categoryCompare != 0)
                return categoryCompare;
            int priorityCompare = ClipPriority(left.Name).CompareTo(ClipPriority(right.Name));
            if (priorityCompare != 0)
                return priorityCompare;
            return string.CompareOrdinal(left.Name, right.Name);
        }

        private static int ClipCategoryPriority(string category)
        {
            switch (NormalizeCategory(category))
            {
                case "ui":
                    return 0;
                case "dialog":
                    return 1;
                case "cutscene":
                    return 2;
                case "battle":
                    return 3;
                case "locomotion":
                    return 4;
                case "interact":
                    return 5;
                case "customized":
                    return 6;
                case "recovered":
                    return 7;
                case "additive":
                    return 8;
                case "helper":
                    return 9;
                case "standalone":
                    return 10;
                default:
                    return 20;
            }
        }

        private static string NormalizeCategory(string category)
        {
            string key = (category ?? "").Trim().ToLowerInvariant();
            if (key.Length == 0)
                return "standalone";
            if (key == "ui_body" || key == "ui_context" || key == "ui_widget")
                return "ui";
            if (key == "dialog_body")
                return "dialog";
            if (key == "cutscene_body")
                return "cutscene";
            if (key == "battle_body")
                return "battle";
            if (key == "locomotion_body" || key == "move")
                return "locomotion";
            if (key == "interaction_body")
                return "interact";
            if (key == "customized_body")
                return "customized";
            if (key == "controller_helper")
                return "helper";
            if (key == "additive_overlay")
                return "additive";
            if (key == "body")
                return "standalone";
            return key;
        }

        private static string CategoryLabel(string category)
        {
            switch (NormalizeCategory(category))
            {
                case "ui":
                    return "UI";
                case "dialog":
                    return "Dialog";
                case "cutscene":
                    return "Cutscene";
                case "battle":
                    return "Battle";
                case "locomotion":
                    return "Locomotion";
                case "interact":
                    return "Interact";
                case "customized":
                    return "Customized";
                case "recovered":
                    return "Recovered";
                case "additive":
                    return "Additive";
                case "helper":
                    return "Helper";
                case "standalone":
                    return "Standalone";
                default:
                    string key = NormalizeCategory(category);
                    return key.Length == 0 ? "Standalone" : char.ToUpperInvariant(key[0]) + key.Substring(1);
            }
        }

        private static int ClipPriority(string name)
        {
            string key = (name ?? "").ToLowerInvariant();
            if (key.Contains("_dialog_"))
                return 0;
            if (key.Contains("_cs_"))
                return 1;
            if (key.Contains("_battle_"))
                return 2;
            if (key.Contains("_walk_") || key.Contains("_sprint_") || key.Contains("_run_"))
                return 3;
            if (key.Contains("_ui_") || key.Contains("uiteam"))
                return 4;
            return 5;
        }

        private ClipEntry BuildClipEntry(string name)
        {
            var entry = new ClipEntry
            {
                Name = name,
                ClipClass = InferClipClass(name),
                ClipCategory = InferClipClass(name),
                LayerRole = "",
                StandaloneCandidate = !IsHelperClipName(name),
                HelperOrAdditive = IsHelperClipName(name),
                SearchText = name ?? "",
            };
            if (activeRig != null && activeRig.clipMetadata != null)
            {
                foreach (CharacterRecoveryClipMetadata metadata in activeRig.clipMetadata)
                {
                    if (metadata == null || metadata.name != name)
                        continue;
                    entry.ClipClass = string.IsNullOrEmpty(metadata.clipClass) ? entry.ClipClass : metadata.clipClass;
                    entry.ClipCategory = string.IsNullOrEmpty(metadata.clipCategory) ? entry.ClipClass : metadata.clipCategory;
                    entry.LayerRole = metadata.layerRole ?? "";
                    entry.StandaloneCandidate = metadata.standaloneCandidate;
                    entry.HelperOrAdditive = metadata.helperOrAdditive || entry.HelperOrAdditive;
                    entry.HelperOrAdditive = entry.HelperOrAdditive || IsHelperClass(entry.ClipClass, entry.LayerRole);
                    entry.WidgetPropPath = metadata.widgetPropPath ?? "";
                    entry.AutoHelperClip = metadata.autoHelperClip ?? "";
                    entry.CombinationNote = metadata.combinationNote ?? "";
                    entry.Note = metadata.note ?? "";
                    entry.SearchText = string.IsNullOrEmpty(metadata.searchText) ? "" : metadata.searchText;
                    break;
                }
            }
            if (string.IsNullOrEmpty(entry.ClipCategory))
                entry.ClipCategory = entry.ClipClass;
            if (string.IsNullOrEmpty(entry.SearchText))
                entry.SearchText = BuildClipSearchText(entry);
            return entry;
        }

        private static string BuildClipSearchText(ClipEntry entry)
        {
            if (entry == null)
                return "";
            return string.Join(
                " ",
                new[]
                {
                    entry.Name ?? "",
                    entry.ClipClass ?? "",
                    entry.ClipCategory ?? "",
                    entry.LayerRole ?? "",
                    entry.WidgetPropPath ?? "",
                    entry.AutoHelperClip ?? "",
                    entry.CombinationNote ?? "",
                    entry.Note ?? "",
                });
        }

        private RecoveredStateEntry BuildRecoveredStateEntry(CharacterRecoveryState source)
        {
            var entry = new RecoveredStateEntry();
            if (source == null)
                return entry;

            entry.Label = source.label ?? "";
            entry.BaseClip = source.baseClip ?? "";
            entry.Source = source.source ?? "";
            entry.Confidence = source.confidence ?? "";
            entry.Note = source.note ?? "";
            if (source.evidenceClips != null)
            {
                foreach (string clip in source.evidenceClips)
                {
                    if (!string.IsNullOrEmpty(clip))
                        entry.EvidenceClips.Add(clip);
                }
            }
            if (source.visibleProps != null)
            {
                foreach (string path in source.visibleProps)
                {
                    if (!string.IsNullOrEmpty(path))
                        entry.VisibleProps.Add(path);
                }
            }
            if (source.layers != null)
            {
                foreach (CharacterRecoveryLayer layer in source.layers)
                {
                    if (layer == null || string.IsNullOrEmpty(layer.clip))
                        continue;
                    entry.Layers.Add(new RecoveredLayerEntry
                    {
                        Clip = layer.clip,
                        Layer = Mathf.Max(1, layer.layer),
                        Additive = layer.additive,
                        Weight = Mathf.Clamp01(layer.weight <= 0f ? 1f : layer.weight),
                        Role = layer.role ?? "",
                        UseControllerLoop = layer.useControllerLoop,
                        ControllerLoop = layer.controllerLoop,
                    });
                }
            }
            if (string.IsNullOrEmpty(entry.Label))
                entry.Label = entry.BaseClip;
            ClipEntry baseEntry = FindClipEntry(entry.BaseClip);
            entry.ClipCategory = baseEntry != null ? baseEntry.ClipCategory : "recovered";
            entry.SearchText = BuildRecoveredStateSearchText(entry, baseEntry);
            return entry;
        }

        private void RebuildStateTransitions()
        {
            stateTransitions.Clear();
            var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (ClipEntry clip in allClips)
            {
                if (clip == null ||
                    string.IsNullOrEmpty(clip.Name) ||
                    !clip.Name.StartsWith("A_actor_", StringComparison.OrdinalIgnoreCase) ||
                    !TryParseStateTransition(clip.Name, out string fromState, out string toState))
                {
                    continue;
                }

                string loopClip = FindDestinationLoopClip(toState);
                if (string.IsNullOrEmpty(loopClip) ||
                    activeAnimation == null ||
                    activeAnimation[clip.Name] == null ||
                    activeAnimation[loopClip] == null)
                    continue;
                string key = fromState + "\n" + toState + "\n" + clip.Name;
                if (!seen.Add(key))
                    continue;
                stateTransitions.Add(new StateTransitionEntry
                {
                    FromState = StateDisplayName(fromState),
                    ToState = StateDisplayName(toState),
                    TransitionClip = clip.Name,
                    LoopClip = loopClip,
                });
            }

            stateTransitions.Sort(CompareStateTransitions);
            RefreshStateTransitionButtons();
        }

        private static bool TryParseStateTransition(
            string clipName,
            out string fromState,
            out string toState)
        {
            fromState = "";
            toState = "";
            if (string.IsNullOrEmpty(clipName))
                return false;
            int uiIndex = clipName.IndexOf("_ui_", StringComparison.OrdinalIgnoreCase);
            if (uiIndex < 0)
                return false;
            string tail = StripNumericClipSuffix(clipName.Substring(uiIndex + 4));
            int separator = tail.IndexOf("_to_", StringComparison.OrdinalIgnoreCase);
            if (separator <= 0 || separator + 4 >= tail.Length)
                return false;
            fromState = NormalizeStateToken(tail.Substring(0, separator).Trim('_').ToLowerInvariant());
            toState = NormalizeStateToken(tail.Substring(separator + 4).Trim('_').ToLowerInvariant());
            return !string.IsNullOrEmpty(fromState) && !string.IsNullOrEmpty(toState);
        }

        private static string NormalizeStateToken(string token)
        {
            // Source clips ship with a few misspelled state tokens.
            switch (token)
            {
                case "ungrade":
                    return "upgrade";
                case "eqiup":
                    return "equip";
                default:
                    return token;
            }
        }

        private static IEnumerable<string> StateTokenAliases(string token)
        {
            yield return token;
            if (token == "upgrade")
                yield return "ungrade";
            if (token == "equip")
                yield return "eqiup";
        }

        private string FindDestinationLoopClip(string destination)
        {
            if (string.IsNullOrEmpty(destination))
                return "";
            var suffixes = new List<string>();
            if (destination.Equals("overview", StringComparison.OrdinalIgnoreCase))
            {
                suffixes.Add("_ui_overview_loop");
            }
            else
            {
                foreach (string alias in StateTokenAliases(destination.ToLowerInvariant()))
                {
                    suffixes.Add("_ui_overview_" + alias + "_loop");
                    suffixes.Add("_ui_" + alias + "_loop");
                    suffixes.Add("_ui_overview_to_" + alias + "_loop");
                }
            }
            foreach (string suffix in suffixes)
            {
                foreach (ClipEntry candidate in allClips)
                {
                    if (candidate == null || string.IsNullOrEmpty(candidate.Name))
                        continue;
                    string stem = StripNumericClipSuffix(candidate.Name);
                    if (stem.EndsWith(suffix, StringComparison.OrdinalIgnoreCase))
                        return candidate.Name;
                }
            }
            return "";
        }

        private static string StripNumericClipSuffix(string value)
        {
            if (string.IsNullOrEmpty(value))
                return "";
            int separator = value.LastIndexOf('_');
            if (separator < 0 || separator + 1 >= value.Length)
                return value;
            for (int index = separator + 1; index < value.Length; index++)
            {
                if (!char.IsDigit(value[index]))
                    return value;
            }
            return value.Substring(0, separator);
        }

        private static string StateDisplayName(string state)
        {
            if (string.IsNullOrEmpty(state))
                return "Unknown";
            string[] words = state.Split(new[] { '_' }, StringSplitOptions.RemoveEmptyEntries);
            for (int index = 0; index < words.Length; index++)
            {
                string word = words[index];
                words[index] = word.Length == 0
                    ? word
                    : char.ToUpperInvariant(word[0]) + word.Substring(1);
            }
            return string.Join(" ", words);
        }

        private static int CompareStateTransitions(StateTransitionEntry left, StateTransitionEntry right)
        {
            string leftPair = StatePairKey(left);
            string rightPair = StatePairKey(right);
            int pair = string.Compare(leftPair, rightPair, StringComparison.OrdinalIgnoreCase);
            if (pair != 0)
                return pair;
            bool leftFromOverview = left != null && left.FromState == "Overview";
            bool rightFromOverview = right != null && right.FromState == "Overview";
            if (leftFromOverview != rightFromOverview)
                return leftFromOverview ? -1 : 1;
            return string.Compare(
                left != null ? left.TransitionClip : "",
                right != null ? right.TransitionClip : "",
                StringComparison.OrdinalIgnoreCase);
        }

        private static string StatePairKey(StateTransitionEntry transition)
        {
            if (transition == null)
                return "";
            string first = transition.FromState ?? "";
            string second = transition.ToState ?? "";
            if (string.Compare(first, second, StringComparison.OrdinalIgnoreCase) > 0)
            {
                string swap = first;
                first = second;
                second = swap;
            }
            return first + "\n" + second;
        }

        private ClipEntry FindClipEntry(string name)
        {
            if (string.IsNullOrEmpty(name))
                return null;
            foreach (ClipEntry entry in allClips)
            {
                if (entry != null && entry.Name == name)
                    return entry;
            }
            return null;
        }

        private static string BuildRecoveredStateSearchText(RecoveredStateEntry entry, ClipEntry baseEntry)
        {
            if (entry == null)
                return "";
            var pieces = new List<string>
            {
                entry.Label ?? "",
                entry.BaseClip ?? "",
                entry.Source ?? "",
                entry.Confidence ?? "",
                entry.Note ?? "",
                entry.ClipCategory ?? "",
                baseEntry != null ? baseEntry.SearchText : "",
            };
            pieces.AddRange(entry.EvidenceClips);
            pieces.AddRange(entry.VisibleProps);
            foreach (RecoveredLayerEntry layer in entry.Layers)
            {
                if (layer == null)
                    continue;
                pieces.Add(layer.Clip ?? "");
                pieces.Add(layer.Role ?? "");
            }
            return string.Join(" ", pieces.ToArray());
        }

        private static string InferClipClass(string name)
        {
            string key = (name ?? "").ToLowerInvariant();
            if (IsHelperClipName(name))
                return key.Contains("additive") ? "additive" : "helper";
            if (key.Contains("_cs_") || key.Contains("cutscene"))
                return "cutscene";
            if (key.Contains("_ui_") || key.Contains("uiteam") || key.Contains("gacha") || key.Contains("uigo"))
                return "ui";
            if (key.Contains("dialog") || key.Contains("dlgtl"))
                return "dialog";
            if (key.Contains("battle") || key.Contains("attack") || key.Contains("skill") || key.Contains("hurt") || key.Contains("dash") || key.Contains("guard") || key.Contains("stun") || key.Contains("knock") || key.Contains("poise") || key.Contains("airborne") || key.Contains("blowoff"))
                return "battle";
            if (key.Contains("customized"))
                return "customized";
            if (key.Contains("interact"))
                return "interact";
            if (key.Contains("_walk_") || key.Contains("_run_") || key.Contains("_sprint_") || key.Contains("_jump_") || key.Contains("_idle_") || key.Contains("locomotion"))
                return "locomotion";
            return "standalone";
        }

        private static bool IsHelperClass(string clipClass, string layerRole)
        {
            string klass = (clipClass ?? "").ToLowerInvariant();
            string role = (layerRole ?? "").ToLowerInvariant();
            return klass == "helper"
                || klass == "additive"
                || role == "controller_helper"
                || role == "additive_overlay";
        }

        private static bool IsHelperClipName(string name)
        {
            string key = (name ?? "").ToLowerInvariant();
            return key.Contains("_additive")
                || key.Contains("_cloth_")
                || key.Contains("_cloth")
                || key.Contains("_tail_")
                || key.Contains("onlycloth")
                || key.Contains("lookat")
                || key.Contains("_ao_")
                || key.Contains("_tilt_")
                || key.Contains("t_pose")
                || key.Contains("_wind_loop_additive")
                || key.EndsWith("_ik_l", StringComparison.Ordinal)
                || key.EndsWith("_ik_r", StringComparison.Ordinal);
        }

        private static List<string> ClipLabels(List<ClipEntry> entries)
        {
            var labels = new List<string>();
            foreach (ClipEntry entry in entries)
                labels.Add(ClipLabel(entry));
            return labels;
        }

        private static List<string> RecoveredStateLabels(List<RecoveredStateEntry> entries)
        {
            var labels = new List<string>();
            foreach (RecoveredStateEntry entry in entries)
            {
                if (entry == null)
                    labels.Add("");
                else if (!string.IsNullOrEmpty(entry.Confidence))
                    labels.Add(entry.Label + "  [" + entry.Confidence + "]");
                else
                    labels.Add(entry.Label);
            }
            return labels;
        }

        private List<string> CurrentClipDropdownLabels()
        {
            return clipMode == ClipMode.RecoveredState
                ? RecoveredStateLabels(visibleRecoveredStates)
                : ClipLabels(visibleClips);
        }

        private int CurrentClipDropdownCount()
        {
            return clipMode == ClipMode.RecoveredState ? visibleRecoveredStates.Count : clipNames.Count;
        }

        private string CurrentSelectionKey()
        {
            return clipMode == ClipMode.RecoveredState && !string.IsNullOrEmpty(activeRecoveredStateLabel)
                ? activeRecoveredStateLabel
                : activeClipName;
        }

        private int SelectionIndexFor(string selection)
        {
            if (string.IsNullOrEmpty(selection))
                return 0;
            if (clipMode == ClipMode.RecoveredState)
            {
                for (int i = 0; i < visibleRecoveredStates.Count; i++)
                {
                    RecoveredStateEntry entry = visibleRecoveredStates[i];
                    if (entry != null && (entry.Label == selection || entry.BaseClip == selection))
                        return i;
                }
                return 0;
            }
            int index = clipNames.IndexOf(selection);
            return index < 0 ? 0 : index;
        }

        private void RebuildClipDropdownUi(int selectedIndex)
        {
            clipDropdown.ClearOptions();
            int dropdownCount = CurrentClipDropdownCount();
            clipDropdown.AddOptions(dropdownCount > 0 ? CurrentClipDropdownLabels() : new List<string> { "No clips" });
            clipDropdown.interactable = dropdownCount > 0;
            clipDropdown.value = dropdownCount > 0 ? Mathf.Clamp(selectedIndex, 0, dropdownCount - 1) : 0;
            clipDropdown.RefreshShownValue();
            UpdateClipFilterSummary();
        }

        private static string ClipLabel(ClipEntry entry)
        {
            if (entry == null)
                return "";
            var tags = new List<string>();
            string category = CategoryLabel(entry.ClipCategory);
            if (!string.IsNullOrEmpty(category) && category != "Standalone")
                tags.Add(category);
            if (entry.HelperOrAdditive)
                tags.Add(entry.ClipClass == "additive" ? "additive" : "helper");
            else if (!string.IsNullOrEmpty(entry.ClipClass) && entry.ClipClass != "standalone" && !string.Equals(entry.ClipClass, entry.ClipCategory, StringComparison.OrdinalIgnoreCase))
                tags.Add(entry.ClipClass);

            string name = string.IsNullOrEmpty(entry.Name) ? "(unnamed clip)" : entry.Name;
            return tags.Count > 0 ? name + "  [" + string.Join(" / ", tags.ToArray()) + "]" : name;
        }

        private void RefreshClipCategoryDropdown()
        {
            var categories = new HashSet<string>();
            if (clipMode == ClipMode.RecoveredState)
            {
                foreach (RecoveredStateEntry entry in recoveredStates)
                {
                    if (entry != null)
                        categories.Add(NormalizeCategory(entry.ClipCategory));
                }
            }
            else
            {
                foreach (ClipEntry entry in allClips)
                {
                    if (entry == null)
                        continue;
                    if (clipMode == ClipMode.Primary && entry.HelperOrAdditive)
                        continue;
                    if (clipMode == ClipMode.Helper && !entry.HelperOrAdditive)
                        continue;
                    categories.Add(NormalizeCategory(entry.ClipCategory));
                }
            }

            var sorted = new List<string>(categories);
            sorted.Sort((left, right) =>
            {
                int priority = ClipCategoryPriority(left).CompareTo(ClipCategoryPriority(right));
                return priority != 0 ? priority : string.CompareOrdinal(CategoryLabel(left), CategoryLabel(right));
            });

            clipCategoryOptions.Clear();
            clipCategoryOptions.Add("");
            clipCategoryOptions.AddRange(sorted);
            if (!string.IsNullOrEmpty(selectedClipCategory) && !clipCategoryOptions.Contains(selectedClipCategory))
                selectedClipCategory = "";

            var labels = new List<string> { "All categories" };
            foreach (string category in sorted)
                labels.Add(CategoryLabel(category));

            updatingUi = true;
            clipCategoryDropdown.ClearOptions();
            clipCategoryDropdown.AddOptions(labels);
            clipCategoryDropdown.value = Mathf.Max(0, clipCategoryOptions.IndexOf(selectedClipCategory));
            clipCategoryDropdown.interactable = sorted.Count > 1;
            clipCategoryDropdown.RefreshShownValue();
            updatingUi = false;
        }

        private bool MatchesClipFilters(ClipEntry entry)
        {
            if (entry == null)
                return false;
            if (!string.IsNullOrEmpty(selectedClipCategory) && NormalizeCategory(entry.ClipCategory) != selectedClipCategory)
                return false;
            return MatchesSearch(entry.SearchText);
        }

        private bool MatchesRecoveredStateFilters(RecoveredStateEntry entry)
        {
            if (entry == null)
                return false;
            if (!string.IsNullOrEmpty(selectedClipCategory) && NormalizeCategory(entry.ClipCategory) != selectedClipCategory)
                return false;
            return MatchesSearch(entry.SearchText);
        }

        private bool MatchesSearch(string text)
        {
            string query = (clipSearchQuery ?? "").Trim().ToLowerInvariant();
            if (query.Length == 0)
                return true;
            string haystack = (text ?? "").ToLowerInvariant();
            string[] terms = query.Split(new[] { ' ', '\t', ',', ';' }, StringSplitOptions.RemoveEmptyEntries);
            foreach (string term in terms)
            {
                if (!haystack.Contains(term))
                    return false;
            }
            return true;
        }

        private void UpdateClipFilterSummary()
        {
            if (clipFilterSummaryText == null)
                return;
            int visible = CurrentClipDropdownCount();
            int total = clipMode == ClipMode.RecoveredState
                ? recoveredStates.Count
                : clipMode == ClipMode.Helper
                    ? helperClips.Count
                    : clipMode == ClipMode.Primary
                        ? CountPrimaryClips()
                        : allClips.Count;
            string category = string.IsNullOrEmpty(selectedClipCategory) ? "All" : CategoryLabel(selectedClipCategory);
            string query = string.IsNullOrEmpty(clipSearchQuery) ? "" : " / search: " + clipSearchQuery;
            clipFilterSummaryText.text = visible.ToString() + " / " + total.ToString() + " clips / " + category + query;
        }

        private int CountPrimaryClips()
        {
            int count = 0;
            foreach (ClipEntry entry in allClips)
            {
                if (entry != null && !entry.HelperOrAdditive && entry.StandaloneCandidate)
                    count++;
            }
            return count;
        }

        private void SelectModel(int index)
        {
            CancelStateTransitionPlayback();
            if (index < 0 || index >= models.Count)
            {
                activeModel = null;
                activeRig = null;
                activeAnimation = null;
                activePoseCorrection = null;
                activeClipName = "";
                activeHelperClipName = "";
                activeRecoveredStateLabel = "";
                activeRecoveredState = null;
                activeLogicalState = "";
                activeRecoveredLayers.Clear();
                allClips.Clear();
                RebuildStateTransitions();
                statusText.text = "No animated model found";
                return;
            }

            ModelEntry model = models[index];
            bool selectionChanged = activeModel != model;
            if (!keepAllModelsResident)
                UnloadInactiveRuntimeInstances(model);
            activeRig = EnsureModelLoaded(model);
            if (activeRig == null)
            {
                activeAnimation = null;
                activePoseCorrection = null;
                activeClipName = "";
                activeHelperClipName = "";
                activeRecoveredStateLabel = "";
                activeRecoveredState = null;
                activeLogicalState = "";
                activeRecoveredLayers.Clear();
                allClips.Clear();
                RebuildStateTransitions();
                statusText.text = "Could not load " + ModelDisplayName(model);
                return;
            }

            activeModel = model;
            if (!keepAllModelsResident)
            {
                foreach (CharacterRecoveryRig rig in rigs)
                {
                    if (rig != null)
                        rig.gameObject.SetActive(rig == activeRig);
                }
            }
            activeRig.gameObject.SetActive(true);
            if (!keepAllModelsResident)
            {
                // Runtime-loaded character prefabs may retain a source/editor
                // staging offset.  The selectable viewer owns one shared
                // CharInfo stage, so every selected actor belongs at its
                // spawn parent's origin.  Resident gallery scenes keep their
                // explicit lineup positions above.
                Transform selectedRoot = activeRig.transform;
                selectedRoot.localPosition = Vector3.zero;
                selectedRoot.localRotation = Quaternion.identity;
                // Clip changes restore this snapshot.  Re-capture after
                // centering so a later sparse-clip reset cannot put the
                // character back at its authored staging offset.
                model.ReferencePose = CharacterLocalPoseSnapshot.Capture(selectedRoot);
            }
            activeAnimation = activeRig.Animation;
            activePoseCorrection = activeRig.PoseCorrection;
            ConfigurePoseControls();
            RefreshClipDropdown();
            if (!ApplyRecoveredPresentation(model))
                FocusCamera();

            if (selectionChanged)
            {
                // The retail Character Info stage enters the actor's recovered
                // Overview start state on every character selection. Resident
                // prefabs remain enabled between selections, so OnEnable alone
                // cannot provide that lifecycle edge.
                model.ReferencePose?.Restore();
                EndfieldOverviewPlayback overview =
                    activeRig.GetComponent<EndfieldOverviewPlayback>();
                if (overview != null)
                    overview.RestartOverviewFromSelection();

                // Native PhaseCharInfo plays the scene-owned CharEffect only
                // after ForceUpdateAnimator. Keep it outside actor/Gacha
                // entrance-effect requests and replay the exact shared stage
                // effect after the same Overview ownership edge.
                EndfieldRecoveredCharInfoSharedEffect sharedEffect =
                    GetComponent<EndfieldRecoveredCharInfoSharedEffect>();
                if (sharedEffect == null)
                    sharedEffect = gameObject.AddComponent<
                        EndfieldRecoveredCharInfoSharedEffect>();
                sharedEffect.PlayAfterOverviewAnimator(activeRig.transform);
            }
        }

        private void UnloadInactiveRuntimeInstances(ModelEntry selected)
        {
            foreach (ModelEntry model in models)
            {
                if (model == null ||
                    model == selected ||
                    !model.RuntimeInstance ||
                    model.Rig == null)
                {
                    continue;
                }

                CharacterRecoveryRig rig = model.Rig;
                rig.gameObject.SetActive(false);
                rigs.Remove(rig);
                Destroy(rig.gameObject);
                model.Rig = null;
                model.RuntimeInstance = false;
                model.ReferencePose = null;
            }
        }

        private CharacterRecoveryRig EnsureModelLoaded(ModelEntry model)
        {
            if (model == null)
                return null;
            if (model.Rig != null)
                return model.Rig;

            GameObject prefab = model.Prefab;
#if UNITY_EDITOR
            if (prefab == null && !string.IsNullOrEmpty(model.PrefabAssetPath))
                prefab = AssetDatabase.LoadAssetAtPath<GameObject>(model.PrefabAssetPath);
#endif
            if (prefab == null)
            {
                Debug.LogWarning(
                    $"Missing runtime character prefab fallback: {model.PrefabAssetPath}");
                return null;
            }

            Transform parent = model.SpawnParent;
            GameObject instance = parent != null
                ? Instantiate(prefab, parent)
                : Instantiate(prefab);
            if (!string.IsNullOrEmpty(model.RootName))
                instance.name = model.RootName;

            CharacterRecoveryRig rig = instance.GetComponent<CharacterRecoveryRig>();
            if (rig == null)
                rig = instance.GetComponentInChildren<CharacterRecoveryRig>(true);
            if (rig == null)
            {
                Animation animation = instance.GetComponent<Animation>();
                if (animation == null)
                    animation = instance.GetComponentInChildren<Animation>(true);
                if (animation != null)
                {
                    rig = animation.GetComponent<CharacterRecoveryRig>();
                    if (rig == null)
                        rig = animation.gameObject.AddComponent<CharacterRecoveryRig>();
                    rig.animationSource = animation;
                }
            }

            if (rig == null)
            {
                Debug.LogWarning($"Loaded character prefab has no CharacterRecoveryRig or Animation: {model.PrefabAssetPath}");
                return null;
            }

            if (!string.IsNullOrEmpty(model.DisplayName))
                rig.displayName = model.DisplayName;
            model.Rig = rig;
            model.RuntimeInstance = true;
            CaptureReferencePose(model, rig);
            if (!rigs.Contains(rig))
                rigs.Add(rig);
            return rig;
        }

        private bool ApplyRecoveredPresentation(ModelEntry model)
        {
            if (model == null ||
                model.PresentationProfile == null ||
                activeRig == null)
            {
                return false;
            }

            CharacterRecoveryPresentationController presentation =
                FindObjectOfType<CharacterRecoveryPresentationController>();
            return presentation != null &&
                   presentation.ApplyProfile(
                       model.PresentationProfile,
                       activeRig);
        }

        private void RefreshClipDropdown()
        {
            allClips.Clear();
            visibleClips.Clear();
            helperClips.Clear();
            recoveredStates.Clear();
            visibleRecoveredStates.Clear();
            activeRecoveredLayers.Clear();
            clipNames.Clear();
            helperClipNames.Clear();
            if (activeAnimation != null)
            {
                foreach (AnimationState state in activeAnimation)
                {
                    if (state != null && state.clip != null)
                        allClips.Add(BuildClipEntry(state.name));
                }
            }
            allClips.Sort(CompareClipEntries);
            foreach (ClipEntry entry in allClips)
            {
                if (entry.HelperOrAdditive)
                    helperClips.Add(entry);
            }
            if (activeRig != null && activeRig.recoveredStates != null)
            {
                foreach (CharacterRecoveryState state in activeRig.recoveredStates)
                {
                    RecoveredStateEntry entry = BuildRecoveredStateEntry(state);
                    if (HasAvailableRecoveredState(entry))
                        recoveredStates.Add(entry);
                }
            }
            foreach (ClipEntry entry in helperClips)
                helperClipNames.Add(entry.Name);
            RebuildStateTransitions();
            RefreshClipCategoryDropdown();
            RefreshVisibleClips();
            string preferredSelection = activeAnimation != null && activeAnimation.clip != null
                ? activeAnimation.clip.name
                : CurrentSelectionKey();
            int defaultIndex = SelectionIndexFor(preferredSelection);

            updatingUi = true;
            RebuildClipDropdownUi(defaultIndex);
            ConfigureHelperDropdownForMode();
            activeHelperClipName = "";
            activeRecoveredStateLabel = "";
            activeRecoveredState = null;
            updatingUi = false;

            selectingInitialClip = true;
            try
            {
                if (clipMode == ClipMode.RecoveredState)
                {
                    SelectClip(visibleRecoveredStates.Count > 0 ? defaultIndex : -1);
                }
                else if (activeAnimation != null && activeAnimation.clip != null)
                {
                    SelectClip(defaultIndex);
                }
                else
                {
                    SelectClip(clipNames.Count > 0 ? 0 : -1);
                }
            }
            finally
            {
                selectingInitialClip = false;
            }
        }

        private bool HasAvailableRecoveredState(RecoveredStateEntry entry)
        {
            if (entry == null || activeAnimation == null || string.IsNullOrEmpty(entry.BaseClip))
                return false;
            if (activeAnimation[entry.BaseClip] == null)
                return false;
            foreach (RecoveredLayerEntry layer in entry.Layers)
            {
                if (layer != null && !string.IsNullOrEmpty(layer.Clip) && activeAnimation[layer.Clip] != null)
                    return true;
            }
            return false;
        }

        private void ConfigureHelperDropdownForMode()
        {
            helperDropdown.ClearOptions();
            if (clipMode == ClipMode.RecoveredState)
            {
                helperDropdown.AddOptions(new List<string> { "Recovered layers" });
                helperDropdown.interactable = false;
                helperDropdown.value = 0;
                return;
            }

            var helperOptions = new List<string> { "None" };
            helperOptions.AddRange(ClipLabels(helperClips));
            helperDropdown.AddOptions(helperOptions);
            helperDropdown.interactable = helperClips.Count > 0;
            helperDropdown.value = 0;
        }

        private void RefreshVisibleClips()
        {
            visibleClips.Clear();
            visibleRecoveredStates.Clear();
            clipNames.Clear();
            if (clipMode == ClipMode.RecoveredState)
            {
                foreach (RecoveredStateEntry entry in recoveredStates)
                {
                    if (!MatchesRecoveredStateFilters(entry))
                        continue;
                    visibleRecoveredStates.Add(entry);
                    clipNames.Add(entry.BaseClip);
                }
                return;
            }
            foreach (ClipEntry entry in allClips)
            {
                if (clipMode == ClipMode.Primary &&
                    (entry.HelperOrAdditive || !entry.StandaloneCandidate))
                    continue;
                if (clipMode == ClipMode.Helper && !entry.HelperOrAdditive)
                    continue;
                if (!MatchesClipFilters(entry))
                    continue;
                visibleClips.Add(entry);
                clipNames.Add(entry.Name);
            }
            if (visibleClips.Count == 0 && clipMode == ClipMode.Primary && string.IsNullOrEmpty(selectedClipCategory) && string.IsNullOrEmpty(clipSearchQuery))
            {
                foreach (ClipEntry entry in allClips)
                {
                    if (!entry.HelperOrAdditive && entry.StandaloneCandidate)
                    {
                        visibleClips.Add(entry);
                        clipNames.Add(entry.Name);
                    }
                }
            }
        }

        private void SelectClip(int index)
        {
            if (clipMode == ClipMode.RecoveredState)
            {
                SelectRecoveredState(index);
                return;
            }

            if (updatingUi || activeAnimation == null)
                return;
            if (index < 0 || index >= clipNames.Count)
            {
                ShowNoClipMatchStatus();
                return;
            }

            if (!selectingInitialClip)
            {
                CancelStateTransitionPlayback();
                CancelAutomaticOverviewPlayback();
            }
            StopLayerClips();
            activeAnimation.Stop();
            RestoreActiveReferencePose();
            activeClipName = clipNames[index];
            ConfigureRecoveredCompositionForClip(activeClipName);
            RefreshActivePropVisibility();
            ClipEntry activeEntry = index < visibleClips.Count ? visibleClips[index] : null;
            AnimationState state = activeAnimation[activeClipName];
            if (state == null)
                return;

            ApplyAutoHelper(activeEntry);
            state.wrapMode = loopToggle.isOn ? WrapMode.Loop : WrapMode.Once;
            state.speed = speedSlider.value;
            state.layer = 0;
            state.blendMode = AnimationBlendMode.Blend;
            state.weight = 1f;
            activeAnimation.clip = state.clip;
            state.time = 0f;
            activeAnimation.Sample();
            ApplyPoseCorrectionOnce();
            Play();
            SetActiveLogicalState(StateForLoopClip(activeClipName));
            UpdateStatus();
        }

        private void SelectRecoveredState(int index)
        {
            if (updatingUi || activeAnimation == null)
                return;
            if (index < 0 || index >= visibleRecoveredStates.Count)
            {
                ShowNoClipMatchStatus();
                return;
            }

            RecoveredStateEntry entry = visibleRecoveredStates[index];
            if (entry == null || string.IsNullOrEmpty(entry.BaseClip))
                return;
            AnimationState state = activeAnimation[entry.BaseClip];
            if (state == null)
                return;

            if (!selectingInitialClip)
            {
                CancelStateTransitionPlayback();
                CancelAutomaticOverviewPlayback();
            }
            StopLayerClips();
            activeAnimation.Stop();
            RestoreActiveReferencePose();
            SetVisibleProps(VisiblePropsForRecoveredState(entry));
            activeClipName = entry.BaseClip;
            activeHelperClipName = "";
            activeRecoveredStateLabel = entry.Label;
            activeRecoveredState = entry;
            activeRecoveredLayers.Clear();
            foreach (RecoveredLayerEntry layer in entry.Layers)
            {
                if (layer != null && !string.IsNullOrEmpty(layer.Clip) && activeAnimation[layer.Clip] != null)
                    activeRecoveredLayers.Add(layer);
            }

            state.wrapMode = loopToggle.isOn ? WrapMode.Loop : WrapMode.Once;
            state.speed = speedSlider.value;
            state.layer = 0;
            state.blendMode = AnimationBlendMode.Blend;
            state.weight = 1f;
            activeAnimation.clip = state.clip;
            state.time = 0f;
            activeAnimation.Sample();
            ApplyPoseCorrectionOnce();
            Play();
            SetActiveLogicalState(StateForLoopClip(activeClipName));
            UpdateStatus();
        }

        private void CancelAutomaticOverviewPlayback()
        {
            if (activeRig == null)
                return;
            EndfieldOverviewPlayback overviewPlayback =
                activeRig.GetComponent<EndfieldOverviewPlayback>();
            overviewPlayback?.CancelForManualPlayback();
        }

        private void TravelToState(StateButtonEntry target)
        {
            if (target == null || activeAnimation == null || string.IsNullOrEmpty(target.LoopClip))
                return;
            bool alreadyAtTarget = !string.IsNullOrEmpty(activeLogicalState) &&
                activeLogicalState.Equals(target.State, StringComparison.OrdinalIgnoreCase);
            if (alreadyAtTarget && playingStateGraphLoop)
                return;

            var transitionClips = new List<string>();
            if (!alreadyAtTarget)
            {
                StateTransitionEntry direct = FindTransition(activeLogicalState, target.State);
                if (direct != null)
                {
                    transitionClips.Add(direct.TransitionClip);
                }
                else
                {
                    // No direct clip; route through the Overview hub when possible.
                    StateTransitionEntry toOverview =
                        activeLogicalState.Equals("Overview", StringComparison.OrdinalIgnoreCase)
                            ? null
                            : FindTransition(activeLogicalState, "Overview");
                    if (toOverview != null)
                        transitionClips.Add(toOverview.TransitionClip);
                    StateTransitionEntry fromOverview =
                        target.State.Equals("Overview", StringComparison.OrdinalIgnoreCase)
                            ? null
                            : FindTransition("Overview", target.State);
                    if (fromOverview != null)
                        transitionClips.Add(fromOverview.TransitionClip);
                }
                if (transitionClips.Count == 0 &&
                    target.State.Equals("Overview", StringComparison.OrdinalIgnoreCase))
                {
                    string startClip = FindOverviewStartClip();
                    if (!string.IsNullOrEmpty(startClip))
                        transitionClips.Add(startClip);
                }
            }

            CancelStateTransitionPlayback();
            CancelAutomaticOverviewPlayback();
            int generation = ++stateTransitionGeneration;
            stateTransitionCoroutine = StartCoroutine(
                TravelToStateRoutine(target.State, transitionClips, target.LoopClip, generation, activeAnimation));
        }

        private IEnumerator TravelToStateRoutine(
            string targetState,
            List<string> transitionClips,
            string loopClip,
            int generation,
            Animation sourceAnimation)
        {
            playingStateGraphLoop = false;
            for (int index = 0; index < transitionClips.Count; index++)
            {
                string clip = transitionClips[index];
                if (!BeginStateGraphClip(clip, WrapMode.Once, index == 0))
                    yield break;
                playingStateTransitionClip = true;
                if (stateTransitionStatusText != null)
                {
                    stateTransitionStatusText.text =
                        "Transitioning to " + targetState + "\n" + clip;
                }

                AnimationState transitionState = sourceAnimation[clip];
                float elapsedPlayback = 0f;
                float playbackDuration = transitionState != null
                    ? transitionState.length / Mathf.Max(0.0001f, Mathf.Abs(transitionState.speed))
                    : 0f;
                while (generation == stateTransitionGeneration &&
                       activeAnimation == sourceAnimation &&
                       transitionState != null &&
                       transitionState.length > 0f &&
                       elapsedPlayback + 0.0001f < playbackDuration &&
                       sourceAnimation.IsPlaying(clip))
                {
                    elapsedPlayback += Time.unscaledDeltaTime;
                    yield return null;
                }

                if (generation != stateTransitionGeneration || activeAnimation != sourceAnimation)
                    yield break;
            }

            if (!BeginStateGraphClip(loopClip, WrapMode.Loop, transitionClips.Count == 0))
                yield break;

            playingStateTransitionClip = false;
            playingStateGraphLoop = true;
            SetActiveLogicalState(targetState);
            if (stateTransitionStatusText != null)
            {
                stateTransitionStatusText.text =
                    "Current state: " + targetState +
                    "\nLoop: " + loopClip;
            }
            stateTransitionCoroutine = null;
        }

        private StateTransitionEntry FindTransition(string fromState, string toState)
        {
            if (string.IsNullOrEmpty(fromState) || string.IsNullOrEmpty(toState))
                return null;
            foreach (StateTransitionEntry transition in stateTransitions)
            {
                if (transition != null &&
                    transition.FromState.Equals(fromState, StringComparison.OrdinalIgnoreCase) &&
                    transition.ToState.Equals(toState, StringComparison.OrdinalIgnoreCase))
                    return transition;
            }
            return null;
        }

        private string FindOverviewStartClip()
        {
            foreach (ClipEntry candidate in allClips)
            {
                if (candidate == null || string.IsNullOrEmpty(candidate.Name))
                    continue;
                string stem = StripNumericClipSuffix(candidate.Name);
                if (stem.EndsWith("_ui_overview_start", StringComparison.OrdinalIgnoreCase) &&
                    activeAnimation != null &&
                    activeAnimation[candidate.Name] != null)
                    return candidate.Name;
            }
            return "";
        }

        private bool BeginStateGraphClip(string clipName, WrapMode wrapMode, bool restoreReferencePose)
        {
            if (activeAnimation == null || string.IsNullOrEmpty(clipName))
                return false;
            AnimationState state = activeAnimation[clipName];
            if (state == null)
                return false;

            StopLayerClips();
            activeAnimation.Stop();
            if (restoreReferencePose)
                RestoreActiveReferencePose();
            ConfigureRecoveredCompositionForClip(clipName);

            state.layer = 0;
            state.blendMode = AnimationBlendMode.Blend;
            state.wrapMode = wrapMode;
            state.speed = speedSlider != null ? speedSlider.value : 1f;
            state.weight = 1f;
            state.time = 0f;
            activeAnimation.clip = state.clip;
            activeAnimation.Sample();
            activeAnimation.Play(clipName, PlayMode.StopSameLayer);
            ApplyRecoveredLayers();
            RefreshActivePropVisibility();
            EndfieldOverviewPlayback overviewPlayback =
                activeRig != null
                    ? activeRig.GetComponent<EndfieldOverviewPlayback>()
                    : null;
            overviewPlayback?.ApplyManualUiClipComposition(clipName);
            playing = true;
            if (playPauseText != null)
                playPauseText.text = "Pause";
            UpdateStatus();
            return true;
        }

        private void ConfigureRecoveredCompositionForClip(string clipName)
        {
            activeClipName = clipName ?? "";
            activeHelperClipName = "";
            activeRecoveredState = FindRecoveredStateForClip(activeClipName);
            activeRecoveredStateLabel = activeRecoveredState != null
                ? activeRecoveredState.Label
                : "";
            activeRecoveredLayers.Clear();
            if (activeRecoveredState == null)
                return;
            foreach (RecoveredLayerEntry layer in activeRecoveredState.Layers)
            {
                if (layer != null &&
                    !string.IsNullOrEmpty(layer.Clip) &&
                    activeAnimation[layer.Clip] != null)
                {
                    activeRecoveredLayers.Add(layer);
                }
            }
        }

        private RecoveredStateEntry FindRecoveredStateForClip(string clipName)
        {
            if (string.IsNullOrEmpty(clipName))
                return null;
            foreach (RecoveredStateEntry entry in recoveredStates)
            {
                if (entry != null && entry.BaseClip == clipName)
                    return entry;
            }
            return null;
        }

        private void CancelStateTransitionPlayback(bool preserveSettledLoop = false)
        {
            stateTransitionGeneration++;
            playingStateTransitionClip = false;
            if (!preserveSettledLoop)
                playingStateGraphLoop = false;
            if (stateTransitionCoroutine != null)
            {
                StopCoroutine(stateTransitionCoroutine);
                stateTransitionCoroutine = null;
            }
        }

        private string StateForLoopClip(string clipName)
        {
            if (string.IsNullOrEmpty(clipName))
                return "";
            foreach (StateTransitionEntry transition in stateTransitions)
            {
                if (transition != null && transition.LoopClip == clipName)
                    return transition.ToState;
            }
            string stem = StripNumericClipSuffix(clipName);
            if (stem.EndsWith("_ui_overview_start", StringComparison.OrdinalIgnoreCase) ||
                stem.EndsWith("_ui_overview_loop", StringComparison.OrdinalIgnoreCase))
            {
                return "Overview";
            }
            return "";
        }

        private void SetActiveLogicalState(string state)
        {
            activeLogicalState = state ?? "";
            RefreshStateTransitionButtonStyles();
        }

        private void ShowNoClipMatchStatus()
        {
            activeClipName = "";
            activeHelperClipName = "";
            activeRecoveredStateLabel = "";
            activeRecoveredState = null;
            activeRecoveredLayers.Clear();
            SetVisibleProps(Array.Empty<string>());
            if (statusText != null && activeRig != null)
                statusText.text = activeRig.displayName + " / no clips match filters";
        }

        private void ApplyAutoHelper(ClipEntry entry)
        {
            activeHelperClipName = "";
            if (entry == null || string.IsNullOrEmpty(entry.AutoHelperClip))
            {
                SetHelperDropdownValue(0);
                return;
            }

            int helperIndex = helperClipNames.IndexOf(entry.AutoHelperClip);
            if (helperIndex < 0)
            {
                SetHelperDropdownValue(0);
                return;
            }

            activeHelperClipName = entry.AutoHelperClip;
            SetHelperDropdownValue(helperIndex + 1);
        }

        private void SetHelperDropdownValue(int value)
        {
            if (helperDropdown == null)
                return;
            updatingUi = true;
            helperDropdown.value = Mathf.Clamp(value, 0, helperDropdown.options.Count - 1);
            helperDropdown.RefreshShownValue();
            updatingUi = false;
        }

        private void SelectClipMode(int index)
        {
            if (updatingUi)
                return;
            string previousSelection = CurrentSelectionKey();
            clipMode = (ClipMode)Mathf.Clamp(index, 0, 3);
            StopLayerClips();
            activeRecoveredStateLabel = "";
            activeRecoveredLayers.Clear();
            RefreshClipCategoryDropdown();
            RefreshVisibleClips();
            int nextIndex = SelectionIndexFor(previousSelection);

            updatingUi = true;
            int dropdownCount = CurrentClipDropdownCount();
            RebuildClipDropdownUi(nextIndex);
            ConfigureHelperDropdownForMode();
            updatingUi = false;
            SelectClip(dropdownCount > 0 ? nextIndex : -1);
        }

        private void SelectClipCategory(int index)
        {
            if (updatingUi)
                return;
            selectedClipCategory = index >= 0 && index < clipCategoryOptions.Count ? clipCategoryOptions[index] : "";
            string previousSelection = CurrentSelectionKey();
            StopLayerClips();
            activeRecoveredStateLabel = "";
            activeRecoveredLayers.Clear();
            RefreshVisibleClips();
            int nextIndex = SelectionIndexFor(previousSelection);

            updatingUi = true;
            int dropdownCount = CurrentClipDropdownCount();
            RebuildClipDropdownUi(nextIndex);
            ConfigureHelperDropdownForMode();
            updatingUi = false;
            SelectClip(dropdownCount > 0 ? nextIndex : -1);
        }

        private void SetClipSearch(string value)
        {
            if (updatingUi)
                return;
            clipSearchQuery = value ?? "";
            string previousSelection = CurrentSelectionKey();
            StopLayerClips();
            activeRecoveredStateLabel = "";
            activeRecoveredLayers.Clear();
            RefreshVisibleClips();
            int nextIndex = SelectionIndexFor(previousSelection);

            updatingUi = true;
            int dropdownCount = CurrentClipDropdownCount();
            RebuildClipDropdownUi(nextIndex);
            ConfigureHelperDropdownForMode();
            updatingUi = false;
            SelectClip(dropdownCount > 0 ? nextIndex : -1);
        }

        private void SelectHelperClip(int index)
        {
            if (updatingUi || activeAnimation == null)
                return;
            if (clipMode == ClipMode.RecoveredState)
                return;

            StopHelper();
            activeHelperClipName = "";
            int helperIndex = index - 1;
            if (helperIndex >= 0 && helperIndex < helperClipNames.Count)
                activeHelperClipName = helperClipNames[helperIndex];

            if (playing)
                ApplyHelperLayer();
            else if (!string.IsNullOrEmpty(activeHelperClipName))
            {
                ApplyHelperLayer();
                AnimationState helperState = activeAnimation[activeHelperClipName];
                if (helperState != null)
                    helperState.speed = 0f;
                activeAnimation.Sample();
                ApplyPoseCorrectionOnce();
            }
            RefreshActivePropVisibility();
            UpdateStatus();
        }

        private void ApplyHelperLayer()
        {
            if (activeAnimation == null || string.IsNullOrEmpty(activeHelperClipName))
                return;
            AnimationState helperState = activeAnimation[activeHelperClipName];
            if (helperState == null)
                return;
            helperState.layer = 1;
            helperState.blendMode = AnimationBlendMode.Additive;
            helperState.wrapMode = loopToggle.isOn ? WrapMode.Loop : WrapMode.Once;
            helperState.speed = speedSlider.value;
            helperState.weight = 1f;
            SyncHelperTime(helperState);
            activeAnimation.Play(activeHelperClipName);
        }

        private void ApplyRecoveredLayers()
        {
            if (activeAnimation == null || activeRecoveredLayers.Count == 0)
                return;
            for (int i = 0; i < activeRecoveredLayers.Count; i++)
            {
                RecoveredLayerEntry layer = activeRecoveredLayers[i];
                if (layer == null || string.IsNullOrEmpty(layer.Clip))
                    continue;
                AnimationState layerState = activeAnimation[layer.Clip];
                if (layerState == null)
                    continue;
                layerState.layer = Mathf.Max(1, layer.Layer);
                layerState.blendMode = layer.Additive ? AnimationBlendMode.Additive : AnimationBlendMode.Blend;
                layerState.wrapMode = layer.UseControllerLoop
                    ? (layer.ControllerLoop ? WrapMode.Loop : WrapMode.ClampForever)
                    : (loopToggle.isOn ? WrapMode.Loop : WrapMode.Once);
                layerState.speed = speedSlider.value;
                layerState.weight = Mathf.Clamp01(layer.Weight <= 0f ? 1f : layer.Weight);
                SyncLayerTime(layerState);
                activeAnimation.Play(layer.Clip);
            }
        }

        private void StopHelper()
        {
            if (activeAnimation == null || string.IsNullOrEmpty(activeHelperClipName))
                return;
            AnimationState helperState = activeAnimation[activeHelperClipName];
            if (helperState != null)
                helperState.enabled = false;
        }

        private void StopRecoveredLayers()
        {
            if (activeAnimation == null)
                return;
            foreach (RecoveredLayerEntry layer in activeRecoveredLayers)
            {
                if (layer == null || string.IsNullOrEmpty(layer.Clip))
                    continue;
                AnimationState layerState = activeAnimation[layer.Clip];
                if (layerState != null)
                    layerState.enabled = false;
            }
        }

        private void StopLayerClips()
        {
            StopHelper();
            StopRecoveredLayers();
        }

        private IEnumerable<string> VisiblePropsForRecoveredState(RecoveredStateEntry entry)
        {
            var paths = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            if (entry == null)
                return paths;

            AddVisiblePropsForClip(paths, entry.BaseClip);
            foreach (string path in entry.VisibleProps)
            {
                if (!string.IsNullOrEmpty(path))
                    paths.Add(path);
            }
            foreach (RecoveredLayerEntry layer in entry.Layers)
            {
                if (layer != null)
                    AddVisiblePropsForClip(paths, layer.Clip);
            }
            return paths;
        }

        private IEnumerable<string> VisiblePropsForClip(string clipName)
        {
            var paths = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            AddVisiblePropsForClip(paths, clipName);
            return paths;
        }

        private IEnumerable<string> VisiblePropsForActivePlayback()
        {
            var paths = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            AddVisiblePropsForClip(paths, activeClipName);
            AddVisiblePropsForClip(paths, activeHelperClipName);
            if (activeRecoveredState != null)
            {
                foreach (string path in activeRecoveredState.VisibleProps)
                {
                    if (!string.IsNullOrEmpty(path))
                        paths.Add(path);
                }
            }
            foreach (RecoveredLayerEntry layer in activeRecoveredLayers)
            {
                if (layer != null)
                    AddVisiblePropsForClip(paths, layer.Clip);
            }
            return paths;
        }

        private void RefreshActivePropVisibility()
        {
            SetVisibleProps(VisiblePropsForActivePlayback());
        }

        private void AddVisiblePropsForClip(HashSet<string> paths, string clipName)
        {
            string path = PropPathForClip(clipName);
            if (!string.IsNullOrEmpty(path))
                paths.Add(path);
        }

        private string PropPathForClip(string clipName)
        {
            ClipEntry entry = FindClipEntry(clipName);
            if (entry != null && !string.IsNullOrEmpty(entry.WidgetPropPath))
                return entry.WidgetPropPath;

            // Compatibility fallback for older generated Wulfa prefabs. New
            // manifests serialize the exact private widget root on every clip.
            string lower = (clipName ?? "").ToLowerInvariant();
            if (!lower.Contains("item_widget"))
                return "";
            if (lower.Contains("_wulfa_02_"))
                return "RecoveredProps/Wulfa_Deco_2_Item_Widget_02";
            if (lower.Contains("_wulfa_01_"))
                return "RecoveredProps/Wulfa_Deco_4_Item_Widget_01";
            return "";
        }

        private void SetVisibleProps(IEnumerable<string> visibleProps)
        {
            if (activeRig == null)
                return;

            Transform propRoot = activeRig.transform.Find("RecoveredProps");
            if (propRoot == null)
                return;

            foreach (Renderer renderer in propRoot.GetComponentsInChildren<Renderer>(true))
            {
                if (renderer != null)
                    renderer.enabled = false;
            }

            var enabledPaths = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (string path in visibleProps ?? Array.Empty<string>())
            {
                if (string.IsNullOrEmpty(path) || !enabledPaths.Add(path))
                    continue;
                Transform prop = activeRig.transform.Find(path);
                if (prop == null)
                    continue;
                prop.gameObject.SetActive(true);
                foreach (Renderer renderer in prop.GetComponentsInChildren<Renderer>(true))
                {
                    if (renderer != null)
                    {
                        renderer.gameObject.SetActive(true);
                        renderer.enabled = true;
                    }
                }
            }
        }

        private void SampleHelperAtBaseTime()
        {
            if (activeAnimation == null)
                return;
            if (!string.IsNullOrEmpty(activeHelperClipName))
            {
                AnimationState helperState = activeAnimation[activeHelperClipName];
                if (helperState != null)
                    SyncHelperTime(helperState);
            }
            SampleRecoveredLayersAtBaseTime();
        }

        private void SampleRecoveredLayersAtBaseTime()
        {
            if (activeAnimation == null || activeRecoveredLayers.Count == 0)
                return;
            foreach (RecoveredLayerEntry layer in activeRecoveredLayers)
            {
                if (layer == null || string.IsNullOrEmpty(layer.Clip))
                    continue;
                AnimationState layerState = activeAnimation[layer.Clip];
                if (layerState != null)
                    SyncLayerTime(layerState);
            }
        }

        private void SyncHelperTime(AnimationState helperState)
        {
            SyncLayerTime(helperState);
        }

        private void SyncLayerTime(AnimationState helperState)
        {
            if (helperState == null || string.IsNullOrEmpty(activeClipName))
                return;
            AnimationState baseState = activeAnimation[activeClipName];
            if (baseState == null || baseState.length <= 0f || helperState.length <= 0f)
                return;
            float ratio = Mathf.Clamp01(DisplayClipTime(baseState) / baseState.length);
            helperState.time = ratio * helperState.length;
        }

        private void ConfigurePoseControls()
        {
            if (poseToggle == null || poseWeightSlider == null || poseWeightText == null)
                return;

            bool available = activePoseCorrection != null && activePoseCorrection.HasConfiguredChains;
            updatingUi = true;
            poseToggle.interactable = available;
            poseWeightSlider.interactable = available;
            if (available)
            {
                float currentWeight = Mathf.Clamp01(activePoseCorrection.weight);
                if (currentWeight <= 0f)
                    currentWeight = Mathf.Clamp01(poseWeightSlider.value);
                poseWeightSlider.value = Mathf.Max(0.05f, currentWeight);
                poseToggle.isOn = activePoseCorrection.enabled
                    && activePoseCorrection.enableLabSolver
                    && activePoseCorrection.weight > 0f;
                poseWeightText.text = "Lab IK " + (poseToggle.isOn ? poseWeightSlider.value.ToString("0.00") : "Off");
            }
            else
            {
                poseToggle.isOn = false;
                poseWeightSlider.value = 0f;
                poseWeightText.text = "Lab IK n/a";
            }
            updatingUi = false;
            ApplyPoseCorrectionSettings();
        }

        private void SetPoseCorrection(bool value)
        {
            if (updatingUi)
                return;
            ApplyPoseCorrectionSettings();
            activeAnimation?.Sample();
            ApplyPoseCorrectionOnce();
            UpdateStatus();
        }

        private void SetPoseWeight(float value)
        {
            if (updatingUi)
                return;
            if (poseWeightText != null)
                poseWeightText.text = "Lab IK " + (poseToggle != null && poseToggle.isOn ? value.ToString("0.00") : "Off");
            ApplyPoseCorrectionSettings();
            activeAnimation?.Sample();
            ApplyPoseCorrectionOnce();
            UpdateStatus();
        }

        private void ApplyPoseCorrectionSettings()
        {
            if (activePoseCorrection == null)
                return;

            bool enabled = poseToggle != null
                && poseToggle.interactable
                && poseToggle.isOn
                && poseWeightSlider != null
                && poseWeightSlider.value > 0f;
            activePoseCorrection.enabled = enabled;
            activePoseCorrection.enableLabSolver = enabled;
            activePoseCorrection.weight = enabled ? Mathf.Clamp01(poseWeightSlider.value) : 0f;
            if (poseWeightText != null && !updatingUi)
                poseWeightText.text = "Lab IK " + (enabled ? activePoseCorrection.weight.ToString("0.00") : "Off");
        }

        private void ApplyPoseCorrectionOnce()
        {
            if (activePoseCorrection == null
                || !activePoseCorrection.enabled
                || !activePoseCorrection.enableLabSolver
                || activePoseCorrection.weight <= 0f)
                return;
            activePoseCorrection.Evaluate();
        }

        private void UpdateStatus()
        {
            if (statusText == null || activeRig == null)
                return;
            string helper = string.IsNullOrEmpty(activeHelperClipName) ? "" : " + " + activeHelperClipName + " [helper]";
            if (activeRecoveredLayers.Count > 0)
                helper = " + " + activeRecoveredLayers.Count.ToString() + " recovered layer" + (activeRecoveredLayers.Count == 1 ? "" : "s");
            string mode = clipMode == ClipMode.Primary
                ? "Primary"
                : clipMode == ClipMode.RecoveredState
                    ? "Recovered"
                    : clipMode == ClipMode.Helper ? "Helpers" : "All";
            string pose = activePoseCorrection != null
                && activePoseCorrection.enabled
                && activePoseCorrection.enableLabSolver
                && activePoseCorrection.weight > 0f
                ? " / Lab IK " + activePoseCorrection.weight.ToString("0.00")
                : "";
            string clip = clipMode == ClipMode.RecoveredState && !string.IsNullOrEmpty(activeRecoveredStateLabel)
                ? activeRecoveredStateLabel
                : activeClipName;
            statusText.text = activeRig.displayName + " / " + mode + " / " + clip + helper + pose;
        }

        private void Play()
        {
            if (activeAnimation == null || string.IsNullOrEmpty(activeClipName))
                return;
            AnimationState state = activeAnimation[activeClipName];
            if (state == null)
                return;
            state.speed = speedSlider.value;
            state.wrapMode = playingStateTransitionClip
                ? WrapMode.Once
                : playingStateGraphLoop
                    ? WrapMode.Loop
                    : (loopToggle.isOn ? WrapMode.Loop : WrapMode.Once);
            state.layer = 0;
            state.blendMode = AnimationBlendMode.Blend;
            state.weight = 1f;
            activeAnimation.Play(activeClipName);
            ApplyHelperLayer();
            ApplyRecoveredLayers();
            RefreshActivePropVisibility();
            playing = true;
            playPauseText.text = "Pause";
        }

        private void Pause()
        {
            if (activeAnimation != null && !string.IsNullOrEmpty(activeClipName))
            {
                AnimationState state = activeAnimation[activeClipName];
                if (state != null)
                    state.speed = 0f;
                AnimationState helperState = !string.IsNullOrEmpty(activeHelperClipName) ? activeAnimation[activeHelperClipName] : null;
                if (helperState != null)
                    helperState.speed = 0f;
                foreach (RecoveredLayerEntry layer in activeRecoveredLayers)
                {
                    AnimationState layerState = layer != null && !string.IsNullOrEmpty(layer.Clip) ? activeAnimation[layer.Clip] : null;
                    if (layerState != null)
                        layerState.speed = 0f;
                }
            }
            playing = false;
            playPauseText.text = "Play";
        }

        private void Restart()
        {
            if (activeAnimation == null || string.IsNullOrEmpty(activeClipName))
                return;
            AnimationState state = activeAnimation[activeClipName];
            if (state == null)
                return;
            CancelStateTransitionPlayback(playingStateGraphLoop);
            RestoreActiveReferencePose();
            state.time = 0f;
            AnimationState helperState = !string.IsNullOrEmpty(activeHelperClipName) ? activeAnimation[activeHelperClipName] : null;
            if (helperState != null)
                helperState.time = 0f;
            foreach (RecoveredLayerEntry layer in activeRecoveredLayers)
            {
                AnimationState layerState = layer != null && !string.IsNullOrEmpty(layer.Clip) ? activeAnimation[layer.Clip] : null;
                if (layerState != null)
                    layerState.time = 0f;
            }
            activeAnimation.Sample();
            ApplyPoseCorrectionOnce();
            EndfieldOverviewPlayback overviewPlayback =
                activeRig != null
                    ? activeRig.GetComponent<EndfieldOverviewPlayback>()
                    : null;
            overviewPlayback?.ApplyManualUiClipComposition(activeClipName);
            Play();
        }

        private void SetSpeed(float value)
        {
            speedText.text = "Speed " + value.ToString("0.00") + "x";
            if (activeAnimation == null || string.IsNullOrEmpty(activeClipName))
                return;
            AnimationState state = activeAnimation[activeClipName];
            if (state != null && playing)
                state.speed = value;
            AnimationState helperState = !string.IsNullOrEmpty(activeHelperClipName) ? activeAnimation[activeHelperClipName] : null;
            if (helperState != null && playing)
                helperState.speed = value;
            foreach (RecoveredLayerEntry layer in activeRecoveredLayers)
            {
                AnimationState layerState = layer != null && !string.IsNullOrEmpty(layer.Clip) ? activeAnimation[layer.Clip] : null;
                if (layerState != null && playing)
                    layerState.speed = value;
            }
        }

        private void SetLoop(bool value)
        {
            if (activeAnimation == null || string.IsNullOrEmpty(activeClipName))
                return;
            AnimationState state = activeAnimation[activeClipName];
            if (state != null)
                state.wrapMode = playingStateTransitionClip
                    ? WrapMode.Once
                    : playingStateGraphLoop
                        ? WrapMode.Loop
                        : (value ? WrapMode.Loop : WrapMode.Once);
            AnimationState helperState = !string.IsNullOrEmpty(activeHelperClipName) ? activeAnimation[activeHelperClipName] : null;
            if (helperState != null)
                helperState.wrapMode = value ? WrapMode.Loop : WrapMode.Once;
            foreach (RecoveredLayerEntry layer in activeRecoveredLayers)
            {
                AnimationState layerState = layer != null && !string.IsNullOrEmpty(layer.Clip) ? activeAnimation[layer.Clip] : null;
                if (layerState != null)
                    layerState.wrapMode = layer.UseControllerLoop
                        ? (layer.ControllerLoop ? WrapMode.Loop : WrapMode.ClampForever)
                        : (value ? WrapMode.Loop : WrapMode.Once);
            }
        }

        private void Seek(float value)
        {
            if (updatingUi || activeAnimation == null || string.IsNullOrEmpty(activeClipName))
                return;
            AnimationState state = activeAnimation[activeClipName];
            if (state == null || state.length <= 0f)
                return;
            state.time = Mathf.Clamp01(value) * state.length;
            SampleHelperAtBaseTime();
            activeAnimation.Sample();
            ApplyPoseCorrectionOnce();
        }

        private void UpdateTimeUi()
        {
            if (draggingTime || activeAnimation == null || string.IsNullOrEmpty(activeClipName))
            {
                SetClipDropdownProgress(0f);
                return;
            }
            AnimationState state = activeAnimation[activeClipName];
            if (state == null || state.length <= 0f)
            {
                SetClipDropdownProgress(0f);
                return;
            }
            float displayTime = DisplayClipTime(state);
            float progress = Mathf.Clamp01(displayTime / state.length);
            updatingUi = true;
            timeSlider.value = progress;
            timeText.text = displayTime.ToString("0.00") + " / " + state.length.ToString("0.00");
            updatingUi = false;
            SetClipDropdownProgress(progress);
        }

        private void SetClipDropdownProgress(float value)
        {
            if (clipDropdownProgressFill != null)
                clipDropdownProgressFill.fillAmount = Mathf.Clamp01(value);
        }

        private float DisplayClipTime(AnimationState state)
        {
            if (state == null || state.length <= 0f)
                return 0f;
            if (state.wrapMode == WrapMode.Loop || loopToggle.isOn)
                return Mathf.Repeat(state.time, state.length);
            return Mathf.Clamp(state.time, 0f, state.length);
        }

        private void HandleKeyboard()
        {
            if (EventSystem.current != null && EventSystem.current.currentSelectedGameObject != null)
            {
                var field = EventSystem.current.currentSelectedGameObject.GetComponentInParent<InputField>();
                if (field != null)
                    return;
            }
            if (Input.GetKeyDown(KeyCode.Space))
            {
                if (playing)
                    Pause();
                else
                    Play();
            }
            if (Input.GetKeyDown(KeyCode.R))
                Restart();
            if (Input.GetKeyDown(KeyCode.Home))
                ResetCamera();
            if (Input.GetKeyDown(KeyCode.P) && poseToggle != null && poseToggle.interactable)
                poseToggle.isOn = !poseToggle.isOn;
            if (Input.GetKeyDown(KeyCode.LeftBracket))
                StepClip(-1);
            if (Input.GetKeyDown(KeyCode.RightBracket))
                StepClip(1);
        }

        private void StepClip(int delta)
        {
            int count = CurrentClipDropdownCount();
            if (count == 0)
                return;
            int next = (clipDropdown.value + delta + count) % count;
            clipDropdown.value = next;
            SelectClip(next);
        }

        private void FocusCamera()
        {
            if (activeRig == null)
                return;
            var controller = FindObjectOfType<CharacterRecoveryCameraController>();
            if (controller == null)
                return;
            controller.SetFocus(activeRig.FocusTarget, activeRig.CalculateBounds());
            controller.FrameTarget();
        }

        private void ResetCamera()
        {
            if (activeRig == null)
                return;
            if (ApplyRecoveredPresentation(activeModel))
                return;
            var controller = FindObjectOfType<CharacterRecoveryCameraController>();
            if (controller == null)
                return;
            controller.SetFocus(activeRig.FocusTarget, activeRig.CalculateBounds());
            controller.ResetView();
        }

        private void PopulateResolutionDropdown()
        {
            updatingUi = true;
            resolutionDropdown.ClearOptions();
            var options = new List<string>();
            foreach (Vector2Int option in ResolutionOptions)
                options.Add(ResolutionLabel(option));
            resolutionDropdown.AddOptions(options);
            resolutionDropdown.value = ClosestResolutionIndex(Screen.width, Screen.height);
            resolutionDropdown.RefreshShownValue();
            updatingUi = false;
        }

        private void SelectResolution(int index)
        {
            if (updatingUi || index < 0 || index >= ResolutionOptions.Length)
                return;

            Vector2Int option = ResolutionOptions[index];
#if UNITY_EDITOR
            if (statusText != null)
                statusText.text = "Selected " + ResolutionLabel(option) + " target. Set the Game view size to match in the Editor.";
#else
            Screen.SetResolution(option.x, option.y, FullScreenMode.Windowed);
            if (statusText != null)
                statusText.text = "Resolution " + ResolutionLabel(option);
#endif
        }

        private static int ClosestResolutionIndex(int width, int height)
        {
            if (width <= 0 || height <= 0)
                return 1;

            int best = 0;
            int bestDelta = int.MaxValue;
            for (int i = 0; i < ResolutionOptions.Length; i++)
            {
                Vector2Int option = ResolutionOptions[i];
                int delta = Mathf.Abs(option.x - width) + Mathf.Abs(option.y - height);
                if (delta < bestDelta)
                {
                    best = i;
                    bestDelta = delta;
                }
            }
            return best;
        }

        private static string ResolutionLabel(Vector2Int option)
        {
            return option.x + " x " + option.y;
        }

        private static Font LoadBuiltinUiFont()
        {
            string[] fontNames = { "LegacyRuntime.ttf", "Arial.ttf" };
            foreach (string fontName in fontNames)
            {
                try
                {
                    Font font = Resources.GetBuiltinResource<Font>(fontName);
                    if (font != null)
                        return font;
                }
                catch (ArgumentException)
                {
                    // Unity 6 rejects older built-in font names such as Arial.ttf.
                }
            }
            throw new InvalidOperationException("No built-in Unity UI font is available.");
        }

        private void BuildUi()
        {
            Font font = LoadBuiltinUiFont();
            runtimeUiFont = font;
            var canvasObject = new GameObject("CharacterRecoveryViewerCanvas", typeof(Canvas), typeof(CanvasScaler), typeof(GraphicRaycaster));
            canvasObject.transform.SetParent(transform, false);
            var canvas = canvasObject.GetComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            canvas.sortingOrder = 50;
            var scaler = canvasObject.GetComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1600f, 900f);

            var panel = CreatePanel(canvasObject.transform);
            CreateStateTransitionPanel(canvasObject.transform, font);
            modelDropdown = CreateDropdown(panel.transform, font, "Model", new Vector2(12f, -12f), 300f);
            clipModeDropdown = CreateDropdown(panel.transform, font, "View", new Vector2(12f, -58f), 180f);
            clipModeDropdown.AddOptions(new List<string> { "Primary clips", "Recovered states", "Helper clips", "All clips" });
            clipCategoryDropdown = CreateDropdown(panel.transform, font, "Group", new Vector2(12f, -104f), 180f);
            clipSearchInput = CreateInputField(panel.transform, font, "Search", new Vector2(12f, -150f), 300f);
            clipDropdown = CreateDropdown(panel.transform, font, "Clip", new Vector2(12f, -196f), 300f);
            clipDropdownProgressFill = CreateDropdownProgressFill(clipDropdown);
            helperDropdown = CreateDropdown(panel.transform, font, "Layer", new Vector2(12f, -242f), 300f);
            playPauseButton = CreateButton(panel.transform, font, "Pause", new Vector2(12f, -288f), 82f);
            playPauseText = playPauseButton.GetComponentInChildren<Text>();
            restartButton = CreateButton(panel.transform, font, "Restart", new Vector2(102f, -288f), 82f);
            frameButton = CreateButton(panel.transform, font, "Jump To Figure", new Vector2(192f, -288f), 128f);
            resetCameraButton = CreateButton(panel.transform, font, "Reset Cam", new Vector2(328f, -288f), 108f);
            loopToggle = CreateToggle(panel.transform, font, "Loop", new Vector2(12f, -334f));
            speedSlider = CreateSlider(panel.transform, font, new Vector2(92f, -336f), 162f, 0.05f, 2f, 1f);
            speedText = CreateText(panel.transform, font, "Speed 1.00x", new Vector2(260f, -332f), new Vector2(116f, 24f), TextAnchor.MiddleLeft);
            timeSlider = CreateSlider(panel.transform, font, new Vector2(12f, -378f), 250f, 0f, 1f, 0f);
            timeText = CreateText(panel.transform, font, "0.00 / 0.00", new Vector2(270f, -374f), new Vector2(110f, 24f), TextAnchor.MiddleLeft);
            poseToggle = CreateToggle(panel.transform, font, "Lab IK", new Vector2(12f, -414f));
            poseWeightSlider = CreateSlider(panel.transform, font, new Vector2(92f, -416f), 162f, 0f, 1f, 0.65f);
            poseWeightText = CreateText(panel.transform, font, "Lab IK Off", new Vector2(260f, -412f), new Vector2(116f, 24f), TextAnchor.MiddleLeft);
            resolutionDropdown = CreateDropdown(panel.transform, font, "Res", new Vector2(12f, -452f), 180f);
            clipFilterSummaryText = CreateText(panel.transform, font, "", new Vector2(12f, -496f), new Vector2(420f, 24f), TextAnchor.UpperLeft);
            statusText = CreateText(panel.transform, font, "", new Vector2(12f, -528f), new Vector2(420f, 54f), TextAnchor.UpperLeft);
            PopulateResolutionDropdown();

            modelDropdown.onValueChanged.AddListener(SelectModel);
            clipModeDropdown.onValueChanged.AddListener(SelectClipMode);
            clipCategoryDropdown.onValueChanged.AddListener(SelectClipCategory);
            clipDropdown.onValueChanged.AddListener(SelectClip);
            helperDropdown.onValueChanged.AddListener(SelectHelperClip);
            clipSearchInput.onValueChanged.AddListener(SetClipSearch);
            resolutionDropdown.onValueChanged.AddListener(SelectResolution);
            playPauseButton.onClick.AddListener(() => { if (playing) Pause(); else Play(); });
            restartButton.onClick.AddListener(Restart);
            frameButton.onClick.AddListener(FocusCamera);
            resetCameraButton.onClick.AddListener(ResetCamera);
            loopToggle.onValueChanged.AddListener(SetLoop);
            poseToggle.onValueChanged.AddListener(SetPoseCorrection);
            speedSlider.onValueChanged.AddListener(SetSpeed);
            timeSlider.onValueChanged.AddListener(Seek);
            poseWeightSlider.onValueChanged.AddListener(SetPoseWeight);
            AddSliderDragHooks(timeSlider);
        }

        private void CreateStateTransitionPanel(Transform parent, Font font)
        {
            var panel = new GameObject("StateTransitionPanel", typeof(RectTransform), typeof(Image));
            panel.transform.SetParent(parent, false);
            var rect = panel.GetComponent<RectTransform>();
            rect.anchorMin = new Vector2(1f, 1f);
            rect.anchorMax = new Vector2(1f, 1f);
            rect.pivot = new Vector2(1f, 1f);
            rect.anchoredPosition = new Vector2(-16f, -16f);
            rect.sizeDelta = new Vector2(330f, 420f);
            panel.GetComponent<Image>().color = new Color(0.06f, 0.07f, 0.08f, 0.78f);

            Text title = CreateText(
                panel.transform,
                font,
                "UI states",
                new Vector2(12f, -12f),
                new Vector2(306f, 28f),
                TextAnchor.UpperLeft);
            title.fontSize = 18;
            stateTransitionStatusText = CreateText(
                panel.transform,
                font,
                "Select a character to load its UI states.",
                new Vector2(12f, -44f),
                new Vector2(306f, 48f),
                TextAnchor.UpperLeft);

            var content = new GameObject("Connections", typeof(RectTransform));
            content.transform.SetParent(panel.transform, false);
            var contentRect = content.GetComponent<RectTransform>();
            contentRect.anchorMin = new Vector2(0f, 1f);
            contentRect.anchorMax = new Vector2(0f, 1f);
            contentRect.pivot = new Vector2(0f, 1f);
            contentRect.anchoredPosition = new Vector2(12f, -104f);
            contentRect.sizeDelta = new Vector2(306f, 304f);
            stateTransitionContent = content.transform;
        }

        private void RefreshStateTransitionButtons()
        {
            stateButtons.Clear();
            if (stateTransitionContent == null || runtimeUiFont == null)
                return;
            for (int index = stateTransitionContent.childCount - 1; index >= 0; index--)
            {
                GameObject staleButton = stateTransitionContent.GetChild(index).gameObject;
                staleButton.SetActive(false);
                Destroy(staleButton);
            }

            var loopClipByState = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            foreach (StateTransitionEntry transition in stateTransitions)
            {
                if (transition == null)
                    continue;
                if (!string.IsNullOrEmpty(transition.ToState) &&
                    !loopClipByState.ContainsKey(transition.ToState))
                    loopClipByState[transition.ToState] = transition.LoopClip;
                if (!string.IsNullOrEmpty(transition.FromState) &&
                    !loopClipByState.ContainsKey(transition.FromState))
                {
                    string loop = FindDestinationLoopClip(
                        transition.FromState.Replace(' ', '_').ToLowerInvariant());
                    if (!string.IsNullOrEmpty(loop))
                        loopClipByState[transition.FromState] = loop;
                }
            }

            if (loopClipByState.Count == 0)
            {
                if (stateTransitionStatusText != null)
                {
                    stateTransitionStatusText.text =
                        "No UI states with transition + loop clips are available.";
                }
                return;
            }

            var states = new List<string>(loopClipByState.Keys);
            states.Sort((left, right) =>
            {
                int priority = StatePriority(left).CompareTo(StatePriority(right));
                return priority != 0 ? priority : string.Compare(left, right, StringComparison.OrdinalIgnoreCase);
            });

            const float rowHeight = 40f;
            for (int index = 0; index < states.Count; index++)
            {
                string state = states[index];
                Button button = CreateButton(
                    stateTransitionContent,
                    runtimeUiFont,
                    state,
                    new Vector2(0f, -index * rowHeight),
                    306f);
                var entry = new StateButtonEntry
                {
                    State = state,
                    LoopClip = loopClipByState[state],
                    Button = button,
                };
                button.onClick.AddListener(() => TravelToState(entry));
                stateButtons.Add(entry);
            }

            if (stateTransitionStatusText != null)
            {
                stateTransitionStatusText.text =
                    "Click a state to play its transition, then loop in that state.";
            }
            RefreshStateTransitionButtonStyles();
        }

        private static int StatePriority(string state)
        {
            switch ((state ?? "").ToLowerInvariant())
            {
                case "overview":
                    return 0;
                case "weapon":
                    return 1;
                case "upgrade":
                    return 2;
                case "skill":
                    return 3;
                case "equip":
                    return 4;
                default:
                    return 10;
            }
        }

        private void RefreshStateTransitionButtonStyles()
        {
            foreach (StateButtonEntry row in stateButtons)
            {
                if (row == null || row.Button == null)
                    continue;
                bool current = !string.IsNullOrEmpty(activeLogicalState) &&
                    row.State.Equals(activeLogicalState, StringComparison.OrdinalIgnoreCase);
                bool reachable = !current &&
                    (FindTransition(activeLogicalState, row.State) != null ||
                     FindTransition(activeLogicalState, "Overview") != null ||
                     row.State.Equals("Overview", StringComparison.OrdinalIgnoreCase) ||
                     FindTransition("Overview", row.State) != null);
                Color normal = current
                    ? new Color(0.20f, 0.48f, 0.68f, 0.98f)
                    : reachable
                        ? new Color(0.22f, 0.25f, 0.28f, 0.95f)
                        : new Color(0.16f, 0.17f, 0.19f, 0.85f);
                ColorBlock colors = row.Button.colors;
                colors.normalColor = normal;
                colors.highlightedColor = Color.Lerp(normal, Color.white, 0.18f);
                colors.pressedColor = Color.Lerp(normal, Color.black, 0.18f);
                colors.selectedColor = colors.highlightedColor;
                row.Button.colors = colors;
                Image image = row.Button.GetComponent<Image>();
                if (image != null)
                    image.color = normal;
            }
        }

        private GameObject CreatePanel(Transform parent)
        {
            var panel = new GameObject("Panel", typeof(RectTransform), typeof(Image));
            panel.transform.SetParent(parent, false);
            var rect = panel.GetComponent<RectTransform>();
            rect.anchorMin = new Vector2(0f, 1f);
            rect.anchorMax = new Vector2(0f, 1f);
            rect.pivot = new Vector2(0f, 1f);
            rect.anchoredPosition = new Vector2(16f, -16f);
            rect.sizeDelta = new Vector2(452f, 594f);
            var image = panel.GetComponent<Image>();
            image.color = new Color(0.06f, 0.07f, 0.08f, 0.78f);
            return panel;
        }

        private InputField CreateInputField(Transform parent, Font font, string label, Vector2 pos, float width)
        {
            CreateText(parent, font, label, pos, new Vector2(62f, 32f), TextAnchor.MiddleLeft);
            var go = new GameObject(label + "Input", typeof(RectTransform), typeof(Image), typeof(InputField));
            go.transform.SetParent(parent, false);
            var rect = go.GetComponent<RectTransform>();
            rect.anchorMin = new Vector2(0f, 1f);
            rect.anchorMax = new Vector2(0f, 1f);
            rect.pivot = new Vector2(0f, 1f);
            rect.anchoredPosition = pos + new Vector2(64f, 0f);
            rect.sizeDelta = new Vector2(width, 34f);
            go.GetComponent<Image>().color = new Color(0.13f, 0.15f, 0.17f, 0.95f);

            var input = go.GetComponent<InputField>();
            input.targetGraphic = go.GetComponent<Image>();
            input.lineType = InputField.LineType.SingleLine;
            input.characterLimit = 96;
            input.textComponent = CreateText(go.transform, font, "", new Vector2(8f, -2f), new Vector2(width - 16f, 30f), TextAnchor.MiddleLeft);
            input.placeholder = CreateText(go.transform, font, "clip name, class, layer", new Vector2(8f, -2f), new Vector2(width - 16f, 30f), TextAnchor.MiddleLeft);
            ((Text)input.placeholder).color = new Color(0.55f, 0.6f, 0.65f, 0.9f);
            return input;
        }

        private Dropdown CreateDropdown(Transform parent, Font font, string label, Vector2 pos, float width)
        {
            CreateText(parent, font, label, pos, new Vector2(62f, 32f), TextAnchor.MiddleLeft);
            var go = new GameObject(label + "Dropdown", typeof(RectTransform), typeof(Image), typeof(Dropdown));
            go.transform.SetParent(parent, false);
            var rect = go.GetComponent<RectTransform>();
            rect.anchorMin = new Vector2(0f, 1f);
            rect.anchorMax = new Vector2(0f, 1f);
            rect.pivot = new Vector2(0f, 1f);
            rect.anchoredPosition = pos + new Vector2(64f, 0f);
            rect.sizeDelta = new Vector2(width, 34f);
            go.GetComponent<Image>().color = new Color(0.16f, 0.18f, 0.2f, 0.95f);

            var dropdown = go.GetComponent<Dropdown>();
            dropdown.targetGraphic = go.GetComponent<Image>();
            dropdown.captionText = CreateText(go.transform, font, "", new Vector2(8f, -2f), new Vector2(width - 42f, 30f), TextAnchor.MiddleLeft);
            CreateText(go.transform, font, "v", new Vector2(width - 28f, -2f), new Vector2(20f, 30f), TextAnchor.MiddleCenter);
            BuildDropdownTemplate(dropdown, font, width);
            return dropdown;
        }

        private Image CreateDropdownProgressFill(Dropdown dropdown)
        {
            var track = new GameObject("PlaybackProgressTrack", typeof(RectTransform), typeof(Image));
            track.transform.SetParent(dropdown.transform, false);
            var trackRect = track.GetComponent<RectTransform>();
            trackRect.anchorMin = new Vector2(0f, 0f);
            trackRect.anchorMax = new Vector2(1f, 0f);
            trackRect.pivot = new Vector2(0.5f, 0f);
            trackRect.offsetMin = new Vector2(1f, 1f);
            trackRect.offsetMax = new Vector2(-1f, 5f);
            track.GetComponent<Image>().color = new Color(0.05f, 0.06f, 0.07f, 0.9f);

            var fill = new GameObject("PlaybackProgressFill", typeof(RectTransform), typeof(Image));
            fill.transform.SetParent(track.transform, false);
            var fillRect = fill.GetComponent<RectTransform>();
            fillRect.anchorMin = Vector2.zero;
            fillRect.anchorMax = Vector2.one;
            fillRect.offsetMin = Vector2.zero;
            fillRect.offsetMax = Vector2.zero;
            var image = fill.GetComponent<Image>();
            image.color = new Color(0.55f, 0.78f, 0.92f, 0.95f);
            image.type = Image.Type.Filled;
            image.fillMethod = Image.FillMethod.Horizontal;
            image.fillOrigin = 0;
            image.fillAmount = 0f;
            return image;
        }

        private void BuildDropdownTemplate(Dropdown dropdown, Font font, float width)
        {
            var template = new GameObject("Template", typeof(RectTransform), typeof(Image), typeof(ScrollRect));
            template.transform.SetParent(dropdown.transform, false);
            var templateRect = template.GetComponent<RectTransform>();
            templateRect.anchorMin = new Vector2(0f, 0f);
            templateRect.anchorMax = new Vector2(1f, 0f);
            templateRect.pivot = new Vector2(0.5f, 1f);
            templateRect.anchoredPosition = new Vector2(0f, -2f);
            templateRect.sizeDelta = new Vector2(0f, 220f);
            template.GetComponent<Image>().color = new Color(0.1f, 0.11f, 0.12f, 0.98f);

            var viewport = new GameObject("Viewport", typeof(RectTransform), typeof(Image), typeof(Mask));
            viewport.transform.SetParent(template.transform, false);
            var viewportRect = viewport.GetComponent<RectTransform>();
            viewportRect.anchorMin = Vector2.zero;
            viewportRect.anchorMax = Vector2.one;
            viewportRect.offsetMin = new Vector2(4f, 4f);
            viewportRect.offsetMax = new Vector2(-4f, -4f);
            viewport.GetComponent<Image>().color = new Color(0.08f, 0.09f, 0.1f, 0.98f);
            viewport.GetComponent<Mask>().showMaskGraphic = false;

            var content = new GameObject("Content", typeof(RectTransform));
            content.transform.SetParent(viewport.transform, false);
            var contentRect = content.GetComponent<RectTransform>();
            contentRect.anchorMin = new Vector2(0f, 1f);
            contentRect.anchorMax = new Vector2(1f, 1f);
            contentRect.pivot = new Vector2(0.5f, 1f);
            contentRect.anchoredPosition = Vector2.zero;
            contentRect.sizeDelta = new Vector2(0f, 32f);

            var item = new GameObject("Item", typeof(RectTransform), typeof(Toggle));
            item.transform.SetParent(content.transform, false);
            var itemRect = item.GetComponent<RectTransform>();
            itemRect.anchorMin = new Vector2(0f, 1f);
            itemRect.anchorMax = new Vector2(1f, 1f);
            itemRect.pivot = new Vector2(0.5f, 1f);
            itemRect.anchoredPosition = Vector2.zero;
            itemRect.sizeDelta = new Vector2(0f, 28f);

            var itemBackground = new GameObject("Item Background", typeof(RectTransform), typeof(Image));
            itemBackground.transform.SetParent(item.transform, false);
            var bgRect = itemBackground.GetComponent<RectTransform>();
            bgRect.anchorMin = Vector2.zero;
            bgRect.anchorMax = Vector2.one;
            bgRect.offsetMin = Vector2.zero;
            bgRect.offsetMax = Vector2.zero;
            itemBackground.GetComponent<Image>().color = new Color(0.16f, 0.18f, 0.2f, 0.95f);

            var checkmark = new GameObject("Item Checkmark", typeof(RectTransform), typeof(Image));
            checkmark.transform.SetParent(item.transform, false);
            var checkRect = checkmark.GetComponent<RectTransform>();
            checkRect.anchorMin = new Vector2(0f, 0.5f);
            checkRect.anchorMax = new Vector2(0f, 0.5f);
            checkRect.pivot = new Vector2(0f, 0.5f);
            checkRect.anchoredPosition = new Vector2(8f, 0f);
            checkRect.sizeDelta = new Vector2(10f, 10f);
            checkmark.GetComponent<Image>().color = new Color(0.75f, 0.9f, 1f, 1f);

            Text itemLabel = CreateText(item.transform, font, "Option", new Vector2(26f, -2f), new Vector2(width - 44f, 26f), TextAnchor.MiddleLeft);
            var toggle = item.GetComponent<Toggle>();
            toggle.targetGraphic = itemBackground.GetComponent<Image>();
            toggle.graphic = checkmark.GetComponent<Image>();

            var scroll = template.GetComponent<ScrollRect>();
            scroll.content = contentRect;
            scroll.viewport = viewportRect;
            scroll.horizontal = false;
            scroll.movementType = ScrollRect.MovementType.Clamped;

            dropdown.template = templateRect;
            dropdown.itemText = itemLabel;
            template.SetActive(false);
        }

        private Button CreateButton(Transform parent, Font font, string label, Vector2 pos, float width)
        {
            var go = new GameObject(label + "Button", typeof(RectTransform), typeof(Image), typeof(Button));
            go.transform.SetParent(parent, false);
            var rect = go.GetComponent<RectTransform>();
            rect.anchorMin = new Vector2(0f, 1f);
            rect.anchorMax = new Vector2(0f, 1f);
            rect.pivot = new Vector2(0f, 1f);
            rect.anchoredPosition = pos;
            rect.sizeDelta = new Vector2(width, 34f);
            go.GetComponent<Image>().color = new Color(0.22f, 0.25f, 0.28f, 0.95f);
            CreateText(go.transform, font, label, Vector2.zero, rect.sizeDelta, TextAnchor.MiddleCenter);
            return go.GetComponent<Button>();
        }

        private Toggle CreateToggle(Transform parent, Font font, string label, Vector2 pos)
        {
            var go = new GameObject(label + "Toggle", typeof(RectTransform), typeof(Toggle));
            go.transform.SetParent(parent, false);
            var rect = go.GetComponent<RectTransform>();
            rect.anchorMin = new Vector2(0f, 1f);
            rect.anchorMax = new Vector2(0f, 1f);
            rect.pivot = new Vector2(0f, 1f);
            rect.anchoredPosition = pos;
            rect.sizeDelta = new Vector2(72f, 28f);

            var background = new GameObject("Background", typeof(RectTransform), typeof(Image));
            background.transform.SetParent(go.transform, false);
            var bgRect = background.GetComponent<RectTransform>();
            bgRect.anchorMin = new Vector2(0f, 0.5f);
            bgRect.anchorMax = new Vector2(0f, 0.5f);
            bgRect.pivot = new Vector2(0f, 0.5f);
            bgRect.anchoredPosition = Vector2.zero;
            bgRect.sizeDelta = new Vector2(20f, 20f);
            background.GetComponent<Image>().color = new Color(0.16f, 0.18f, 0.2f, 1f);

            var checkmark = new GameObject("Checkmark", typeof(RectTransform), typeof(Image));
            checkmark.transform.SetParent(background.transform, false);
            var markRect = checkmark.GetComponent<RectTransform>();
            markRect.anchorMin = Vector2.zero;
            markRect.anchorMax = Vector2.one;
            markRect.offsetMin = new Vector2(4f, 4f);
            markRect.offsetMax = new Vector2(-4f, -4f);
            checkmark.GetComponent<Image>().color = new Color(0.75f, 0.9f, 1f, 1f);

            CreateText(go.transform, font, label, new Vector2(26f, 1f), new Vector2(44f, 24f), TextAnchor.MiddleLeft);
            var toggle = go.GetComponent<Toggle>();
            toggle.targetGraphic = background.GetComponent<Image>();
            toggle.graphic = checkmark.GetComponent<Image>();
            toggle.isOn = true;
            return toggle;
        }

        private Slider CreateSlider(Transform parent, Font font, Vector2 pos, float width, float min, float max, float value)
        {
            var go = new GameObject("Slider", typeof(RectTransform), typeof(Slider));
            go.transform.SetParent(parent, false);
            var rect = go.GetComponent<RectTransform>();
            rect.anchorMin = new Vector2(0f, 1f);
            rect.anchorMax = new Vector2(0f, 1f);
            rect.pivot = new Vector2(0f, 1f);
            rect.anchoredPosition = pos;
            rect.sizeDelta = new Vector2(width, 24f);

            var background = new GameObject("Background", typeof(RectTransform), typeof(Image));
            background.transform.SetParent(go.transform, false);
            var bgRect = background.GetComponent<RectTransform>();
            bgRect.anchorMin = new Vector2(0f, 0.5f);
            bgRect.anchorMax = new Vector2(1f, 0.5f);
            bgRect.pivot = new Vector2(0.5f, 0.5f);
            bgRect.anchoredPosition = Vector2.zero;
            bgRect.sizeDelta = new Vector2(0f, 4f);
            background.GetComponent<Image>().color = new Color(0.08f, 0.09f, 0.1f, 1f);

            var fillArea = new GameObject("Fill Area", typeof(RectTransform));
            fillArea.transform.SetParent(go.transform, false);
            var fillAreaRect = fillArea.GetComponent<RectTransform>();
            fillAreaRect.anchorMin = new Vector2(0f, 0.5f);
            fillAreaRect.anchorMax = new Vector2(1f, 0.5f);
            fillAreaRect.pivot = new Vector2(0.5f, 0.5f);
            fillAreaRect.anchoredPosition = Vector2.zero;
            fillAreaRect.sizeDelta = new Vector2(-14f, 4f);

            var fill = new GameObject("Fill", typeof(RectTransform), typeof(Image));
            fill.transform.SetParent(fillArea.transform, false);
            var fillRect = fill.GetComponent<RectTransform>();
            fillRect.anchorMin = Vector2.zero;
            fillRect.anchorMax = Vector2.one;
            fillRect.offsetMin = Vector2.zero;
            fillRect.offsetMax = Vector2.zero;
            fill.GetComponent<Image>().color = new Color(0.55f, 0.75f, 0.9f, 1f);

            var handleArea = new GameObject("Handle Slide Area", typeof(RectTransform));
            handleArea.transform.SetParent(go.transform, false);
            var handleAreaRect = handleArea.GetComponent<RectTransform>();
            handleAreaRect.anchorMin = Vector2.zero;
            handleAreaRect.anchorMax = Vector2.one;
            handleAreaRect.offsetMin = new Vector2(7f, 0f);
            handleAreaRect.offsetMax = new Vector2(-7f, 0f);

            var handle = new GameObject("Handle", typeof(RectTransform), typeof(Image));
            handle.transform.SetParent(handleArea.transform, false);
            var handleRect = handle.GetComponent<RectTransform>();
            handleRect.anchorMin = new Vector2(0f, 0.5f);
            handleRect.anchorMax = new Vector2(0f, 0.5f);
            handleRect.pivot = new Vector2(0.5f, 0.5f);
            handleRect.anchoredPosition = Vector2.zero;
            handleRect.sizeDelta = new Vector2(12f, 18f);
            handle.GetComponent<Image>().color = new Color(0.88f, 0.92f, 0.95f, 1f);

            var slider = go.GetComponent<Slider>();
            slider.minValue = min;
            slider.maxValue = max;
            slider.fillRect = fillRect;
            slider.handleRect = handleRect;
            slider.targetGraphic = handle.GetComponent<Image>();
            slider.direction = Slider.Direction.LeftToRight;
            slider.value = value;
            return slider;
        }

        private Text CreateText(Transform parent, Font font, string value, Vector2 pos, Vector2 size, TextAnchor anchor)
        {
            var go = new GameObject("Text", typeof(RectTransform), typeof(Text));
            go.transform.SetParent(parent, false);
            var rect = go.GetComponent<RectTransform>();
            rect.anchorMin = new Vector2(0f, 1f);
            rect.anchorMax = new Vector2(0f, 1f);
            rect.pivot = new Vector2(0f, 1f);
            rect.anchoredPosition = pos;
            rect.sizeDelta = size;
            var text = go.GetComponent<Text>();
            text.font = font;
            text.fontSize = 14;
            text.alignment = anchor;
            text.color = new Color(0.92f, 0.95f, 0.98f, 1f);
            text.text = value;
            return text;
        }

        private void AddSliderDragHooks(Slider slider)
        {
            var trigger = slider.gameObject.AddComponent<EventTrigger>();
            var begin = new EventTrigger.Entry { eventID = EventTriggerType.BeginDrag };
            begin.callback.AddListener(_ => draggingTime = true);
            trigger.triggers.Add(begin);
            var end = new EventTrigger.Entry { eventID = EventTriggerType.EndDrag };
            end.callback.AddListener(_ =>
            {
                draggingTime = false;
                Seek(timeSlider.value);
            });
            trigger.triggers.Add(end);
        }

        private void EnsureEventSystem()
        {
            if (EventSystem.current != null)
                return;
            var go = new GameObject("EventSystem", typeof(EventSystem), typeof(StandaloneInputModule));
            DontDestroyOnLoad(go);
        }
    }
}
