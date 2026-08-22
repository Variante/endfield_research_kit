using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using EndfieldGraphShaderLab;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLabEditor
{
    public static class EndfieldEndminfEntranceVfxProbe
    {
        private const string Pipeline = "Assets/EndfieldGraphShaderLab/Generated/HGCompatRenderPipeline.asset";
        private const string Actor = "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/Prefabs/Endminf.prefab";
        private const string Effects = "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/Effects/Overview/";
        private static readonly string[] Names = { "P_fxui_endminm003_overview_01", "P_fxui_endminm003_overview_02", "P_fxui_endminm003_overview_03", "P_fxui_endminm003_overview_04" };
        // The admitted _02 orb systems serialize exact start delays in the
        // 4.40-4.45 second window and sub-second lifetimes. Keep dense samples
        // around that authored window; whole-second probes skip it entirely.
        private static readonly float[] Times = { 1.75f, 2.25f, 2.75f, 3.5f,
            4.1f, 4.3f, 4.55f, 4.75f };
        private const int Size = 768;

        [Serializable] private sealed class Report { public string schema="endfield.endminf-entrance-vfx-probe.v1"; public string unityVersion; public string graphicsDeviceType; public float sampleTime; public int admittedRenderers; public int failClosedRenderers; public int changedPixels; public long absoluteRgbDifference; public int refractChangedPixels; public long refractAbsoluteRgbDifference; public float refractSampleTime; public string controlPng; public string effectPng; public string refractControlPng; public string refractEffectPng; public string controlSha256; public string effectSha256; public bool passed; }

        [MenuItem("Endfield/Character Recovery Lab/Render Diagnostics/Endminf Entrance VFX Delta")]
        public static void RenderAndValidate()
        {
            HGCompatRenderPipelineAsset pipeline = AssetDatabase.LoadAssetAtPath<HGCompatRenderPipelineAsset>(Pipeline);
            Require(pipeline != null, "Missing HG compatibility pipeline"); GraphicsSettings.renderPipelineAsset = pipeline; QualitySettings.renderPipeline = pipeline;
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            GameObject actor = PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(Actor)) as GameObject;
            Require(actor != null, "Missing Endminf actor prefab"); actor.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);
            EndfieldOverviewPlayback playback = actor.GetComponentInChildren<EndfieldOverviewPlayback>(true);
            Animation animation = playback.animationSource != null ? playback.animationSource : playback.GetComponent<Animation>();
            Require(animation != null && animation[playback.startClip] != null, "Endminf start clip is missing");
            var effectInstances = Names.Select(name => PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(Effects + name + ".prefab")) as GameObject).ToArray();
            Require(effectInstances.All(value => value != null), "Generated Endminf entrance prefab is missing");
            // AnimatorBehaviourPlayEffect's stationary branch passes the main
            // Animator transform's world position/rotation and unit scale to
            // EffectManager.CreateStationaryEffect. It does not retain the
            // authored prefab-root transform or parent the instance.
            foreach (GameObject effect in effectInstances)
            {
                effect.transform.SetPositionAndRotation(animation.transform.position,
                    animation.transform.rotation);
                effect.transform.localScale = Vector3.one;
            }
            ParticleSystemRenderer[] effectRenderers = effectInstances.SelectMany(value => value.GetComponentsInChildren<ParticleSystemRenderer>(true)).ToArray();
            bool[] sourceEnabled = effectRenderers.Select(value => value.enabled).ToArray();
            string isolation = Environment.GetEnvironmentVariable("ENDFIELD_ENDMINF_RENDERER_INDICES");
            HashSet<int> isolatedIndices = string.IsNullOrWhiteSpace(isolation) ? null :
                new HashSet<int>(isolation.Split(',').Select(int.Parse));
            int admitted = sourceEnabled.Count(value => value); int blocked = effectRenderers.Length - admitted;
            foreach (ParticleSystemRenderer value in effectRenderers.Where(value => value.enabled))
            {
                ParticleSystem source = value.GetComponent<ParticleSystem>();
                Debug.Log("Admitted Endminf renderer: " + value.transform.name +
                    " active=" + value.gameObject.activeInHierarchy +
                    " playOnAwake=" + source.main.playOnAwake +
                    " emission=" + source.emission.enabled +
                    " rate=" + source.emission.rateOverTime.constant +
                    " bursts=" + source.emission.burstCount +
                    " lifetime=" + source.main.startLifetime.constant);
            }
            Require(effectRenderers.Length == 70 && blocked >= 0, "Endminf renderer admission census is invalid");
            var cameraObject = new GameObject("Endminf Entrance VFX Probe Camera"); Camera camera = cameraObject.AddComponent<Camera>(); camera.enabled=false; camera.clearFlags=CameraClearFlags.SolidColor; camera.backgroundColor=pipeline.clearColor; camera.fieldOfView=24f; camera.allowHDR=true; camera.depthTextureMode=DepthTextureMode.Depth;
            // Match the source-closed global state used by the proven
            // BaseV2 power/wind renderer probe. Without an exposure producer
            // this compatibility shader deliberately multiplies to black.
            Shader.SetGlobalVector("_ExposureParams", new Vector4(1f, 0f, 0f, 0f));
            Shader.SetGlobalFloat("_EndfieldRecoveredPostSemantics", 0f);
            Renderer[] body = actor.GetComponentsInChildren<Renderer>(true).Where(value => !effectInstances.Any(effect => value.transform.IsChildOf(effect.transform))).ToArray();
            Bounds bounds = body.Where(value => value.enabled).Select(value => value.bounds).Aggregate((a,b)=>{a.Encapsulate(b);return a;}); Frame(camera,bounds);
            string output=Path.GetFullPath(Path.Combine(Application.dataPath,"../scratch/character_recovery/endminf_entrance_vfx_probe"));Directory.CreateDirectory(output);
            foreach(GameObject effect in effectInstances)foreach(ParticleSystem ps in effect.GetComponentsInChildren<ParticleSystem>(true)){ps.Stop(true,ParticleSystemStopBehavior.StopEmittingAndClear);var trails=ps.trails;if(trails.enabled)trails.enabled=false;}
            for(int index=0;index<effectRenderers.Length;index++)effectRenderers[index].enabled=false;
            Color32[] stableControl=Render(camera,null);
            for(int index=0;index<effectRenderers.Length;index++)effectRenderers[index].enabled=sourceEnabled[index]&&(isolatedIndices==null||isolatedIndices.Contains(index));
            Debug.Log("Endminf renderer isolation indices="+(isolatedIndices==null?"all":string.Join(",",isolatedIndices.OrderBy(value=>value)))+
                " enabled="+string.Join(",",Enumerable.Range(0,effectRenderers.Length).Where(index=>effectRenderers[index].enabled).Select(index=>index+":"+effectRenderers[index].transform.name)));
            int bestChanged=-1;long bestDelta=-1;float bestTime=0;Color32[] bestControl=stableControl,bestEffect=null;
            int bestRefractChanged=-1;long bestRefractDelta=-1;float bestRefractTime=0;Color32[] bestRefractControl=null,bestRefractEffect=null;
            foreach(float time in Times){ animation[playback.startClip].time=Mathf.Min(time,animation[playback.startClip].length);animation.Sample();foreach(GameObject effect in effectInstances)foreach(ParticleSystem ps in effect.GetComponentsInChildren<ParticleSystem>(true)){ps.Stop(false,ParticleSystemStopBehavior.StopEmittingAndClear);ps.Play(false);ps.Simulate(time,false,false,true);}int alive=effectInstances.Sum(effect=>effect.GetComponentsInChildren<ParticleSystem>(true).Sum(ps=>ps.particleCount));int admittedAlive=effectRenderers.Where(r=>r.enabled).Sum(r=>r.GetComponent<ParticleSystem>().particleCount);Color32[] visible=Render(camera,null);ParticleSystemRenderer[] refract=effectRenderers.Where(r=>r.enabled&&r.sharedMaterials.Any(m=>m!=null&&m.shader!=null&&(m.shader.name=="Hidden/Endfield/Recovered/Zhuangfy/VFXRefractMRT"||m.shader.name=="Hidden/Endfield/VisualCompatibility/VFXRefract28"))).ToArray();foreach(var r in refract)r.enabled=false;Color32[] withoutRefract=Render(camera,null);foreach(var r in refract)r.enabled=true;int changed=0,refractChanged=0;long delta=0,refractDelta=0;for(int i=0;i<visible.Length;i++){int d=Math.Abs(visible[i].r-stableControl[i].r)+Math.Abs(visible[i].g-stableControl[i].g)+Math.Abs(visible[i].b-stableControl[i].b);delta+=d;if(d>=6)changed++;int rd=Math.Abs(visible[i].r-withoutRefract[i].r)+Math.Abs(visible[i].g-withoutRefract[i].g)+Math.Abs(visible[i].b-withoutRefract[i].b);refractDelta+=rd;if(rd>=6)refractChanged++;}string admittedBounds="none";ParticleSystemRenderer[] liveAdmitted=effectRenderers.Where(r=>r.enabled&&r.GetComponent<ParticleSystem>().particleCount>0).ToArray();if(liveAdmitted.Length>0){Bounds b=liveAdmitted[0].bounds;foreach(ParticleSystemRenderer r in liveAdmitted.Skip(1))b.Encapsulate(r.bounds);Vector3 viewport=camera.WorldToViewportPoint(b.center);admittedBounds=$"center={b.center} size={b.size} viewport={viewport}";}Debug.Log($"Endminf VFX sample time={time} alive={alive} admittedAlive={admittedAlive} changed={changed} rgb={delta} refractChanged={refractChanged} refractRgb={refractDelta} admittedBounds={admittedBounds}");if(changed>bestChanged){bestChanged=changed;bestDelta=delta;bestTime=time;bestEffect=visible;}if(refractChanged>bestRefractChanged){bestRefractChanged=refractChanged;bestRefractDelta=refractDelta;bestRefractTime=time;bestRefractControl=withoutRefract;bestRefractEffect=visible;}}
            string controlPath=Path.Combine(output,"control.png"),effectPath=Path.Combine(output,"admitted_effect.png");Write(controlPath,bestControl);Write(effectPath,bestEffect);
            bool passed=admitted>0 && bestChanged>=64 && bestDelta>=4096;
            string refractControlPath=Path.Combine(output,"refract_disabled.png"),refractEffectPath=Path.Combine(output,"refract_enabled.png");Write(refractControlPath,bestRefractControl);Write(refractEffectPath,bestRefractEffect);
            var report=new Report{unityVersion=Application.unityVersion,graphicsDeviceType=SystemInfo.graphicsDeviceType.ToString(),sampleTime=bestTime,admittedRenderers=admitted,failClosedRenderers=blocked,changedPixels=bestChanged,absoluteRgbDifference=bestDelta,refractChangedPixels=bestRefractChanged,refractAbsoluteRgbDifference=bestRefractDelta,refractSampleTime=bestRefractTime,controlPng=controlPath,effectPng=effectPath,refractControlPng=refractControlPath,refractEffectPng=refractEffectPath,controlSha256=Hash(controlPath),effectSha256=Hash(effectPath),passed=passed};
            File.WriteAllText(Path.Combine(output,"report.json"),JsonUtility.ToJson(report,true)+"\n",new UTF8Encoding(false));
            Require(passed,"Admitted Endminf effects produced no deterministic visible delta");
            Debug.Log($"PASS Endminf entrance VFX delta: time={bestTime} admitted={admitted} blocked={blocked} changed={bestChanged} rgb={bestDelta}");
        }
        private static void Frame(Camera c,Bounds b){float r=Mathf.Max(b.extents.magnitude,.1f),d=r/Mathf.Tan(c.fieldOfView*.5f*Mathf.Deg2Rad);c.transform.position=b.center+new Vector3(0,0,-d*1.2f);c.transform.rotation=Quaternion.LookRotation(b.center-c.transform.position,Vector3.up);c.nearClipPlane=.01f;c.farClipPlane=d+r*4f;}
        private static Color32[] Render(Camera c,string unused){var rt=new RenderTexture(Size,Size,24,RenderTextureFormat.ARGBHalf,RenderTextureReadWrite.Linear);Require(rt.Create(),"render target failed");var old=RenderTexture.active;c.targetTexture=rt;c.Render();RenderTexture.active=rt;var t=new Texture2D(Size,Size,TextureFormat.RGBA32,false,false);t.ReadPixels(new Rect(0,0,Size,Size),0,0);t.Apply();var p=t.GetPixels32();c.targetTexture=null;RenderTexture.active=old;UnityEngine.Object.DestroyImmediate(t);rt.Release();UnityEngine.Object.DestroyImmediate(rt);return p;}
        private static void Write(string path,Color32[] pixels){var t=new Texture2D(Size,Size,TextureFormat.RGBA32,false,false);t.SetPixels32(pixels);t.Apply();File.WriteAllBytes(path,t.EncodeToPNG());UnityEngine.Object.DestroyImmediate(t);}
        private static string Hash(string path){using(var h=SHA256.Create())using(var s=File.OpenRead(path))return BitConverter.ToString(h.ComputeHash(s)).Replace("-","");}
        private static void Require(bool value,string message){if(!value)throw new InvalidOperationException(message);}
    }
}
