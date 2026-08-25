using System;
using UnityEditor;
using UnityEngine;
using A = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsTransformSnapshotAdapter;
using D = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsData;

namespace EndfieldGraphShaderLabEditor
{
    public static class EndfieldSecondaryDynamicsTransformSnapshotAdapterVerifier
    {
        [MenuItem("Endfield/Character Recovery Lab/Verify Endminf Transform Snapshot Adapter")]
        public static void VerifyMenu()
        {
            Verify();
            Debug.Log("Verified source-ordered Endminf Unity Transform snapshots with no writeback.");
        }

        public static void Verify()
        {
            var rootObject = new GameObject("EndminfSnapshotFixture");
            var data = ScriptableObject.CreateInstance<D>();
            try
            {
                string[] names = { "MC_Ribbon2", "MC_Hair", "MC_Ribbon", "MC_Coat" };
                int[] counts = { 6, 30, 20, 70 };
                data.owners = new D.Owner[4];
                Transform shared = null;
                for (int owner = 0; owner < 4; owner++)
                {
                    var paths = new string[counts[owner]];
                    for (int vertex = 0; vertex < paths.Length; vertex++)
                    {
                        paths[vertex] = names[owner] + "/" + vertex;
                        Transform transform = CreatePath(rootObject.transform, paths[vertex]);
                        transform.position = new Vector3(owner, vertex * 0.01f, 0f);
                        if (owner == 0 && vertex == 0) shared = transform;
                    }
                    data.owners[owner] = new D.Owner
                    {
                        ownerPath = names[owner],
                        proxyVertexCount = paths.Length,
                        proxyTransformPaths = paths,
                    };
                }
                // Preserve one duplicate source entry as a separate read lane.
                data.owners[3].proxyTransformPaths[69] = data.owners[0].proxyTransformPaths[0];

                data.colliders = new D.CapsuleCollider[10];
                for (int collider = 0; collider < data.colliders.Length; collider++)
                {
                    string path = "Collider/" + collider;
                    Transform transform = CreatePath(rootObject.transform, path);
                    transform.position = new Vector3(collider * 0.1f, 0.5f, 0f);
                    data.colliders[collider] = new D.CapsuleCollider { transformPath = path };
                }

                var adapter = new A(rootObject.transform, data);
                A.SnapshotFrame first = adapter.Capture();
                Require(first.ActorRootStationary, "initial root stationary");
                Require(first.Owners.Length == 4 && first.Owners[3].CurrentWorldPositions.Length == 70,
                    "source cardinality");
                Require(first.Owners[0].CurrentWorldPositions[0].x ==
                        first.Owners[3].CurrentWorldPositions[69].x,
                    "duplicate source lane preserved");

                Vector3 originalSharedPosition = shared.position;
                shared.position = new Vector3(2.5f, 3.5f, 4.5f);
                Transform colliderZero = rootObject.transform.Find("Collider/0");
                colliderZero.position = new Vector3(7f, 8f, 9f);
                A.SnapshotFrame second = adapter.Capture();
                Require(second.ActorRootStationary, "unchanged actor root");
                Require(second.Owners[0].PreviousWorldPositions[0].x == originalSharedPosition.x,
                    "previous owner value");
                Require(second.Owners[0].CurrentWorldPositions[0].x == 2.5,
                    "current owner value");
                Require(second.Owners[3].CurrentWorldPositions[69].x == 2.5,
                    "duplicate current lane");
                Require(second.PreviousColliderSamples[0].Position.x == 0.0,
                    "previous collider value");
                Require(second.CurrentColliderSamples[0].Position.x == 7.0,
                    "current collider value");
                Require(shared.position == new Vector3(2.5f, 3.5f, 4.5f),
                    "adapter performs no writeback");

                rootObject.transform.position = Vector3.right;
                A.SnapshotFrame moved = adapter.Capture();
                Require(!moved.ActorRootStationary, "root movement fail-closed signal");
                Expect<ArgumentException>(() => new A(rootObject.transform,
                    ScriptableObject.CreateInstance<D>()));
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(data);
                UnityEngine.Object.DestroyImmediate(rootObject);
            }
        }

        private static Transform CreatePath(Transform root, string path)
        {
            Transform current = root;
            foreach (string segment in path.Split('/'))
            {
                Transform child = current.Find(segment);
                if (child == null)
                {
                    var gameObject = new GameObject(segment);
                    child = gameObject.transform;
                    child.SetParent(current, false);
                }
                current = child;
            }
            return current;
        }

        private static void Require(bool condition, string message)
        {
            if (!condition)
                throw new InvalidOperationException(
                    "Transform snapshot adapter verification failed: " + message);
        }

        private static void Expect<T>(Action action) where T : Exception
        {
            try { action(); }
            catch (T) { return; }
            throw new InvalidOperationException("Expected " + typeof(T).Name);
        }
    }
}
