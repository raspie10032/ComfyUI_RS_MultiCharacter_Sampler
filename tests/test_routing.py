"""CPU checks of attention connectivity against explicit dense boolean masks."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest

import torch
import torch.nn.functional as F

spec = importlib.util.spec_from_file_location("routing", Path(__file__).resolve().parents[1] / "routing.py")
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


class RoutingTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(849)
        self.q = torch.randn(2, 8, 2, 4, dtype=torch.float64)
        self.k = torch.randn(2, 9, 2, 4, dtype=torch.float64)
        self.v = torch.randn_like(self.k)
        self.groups = [torch.tensor([0, 2, 4, 6]), torch.tensor([1, 3, 5, 7])]
        self.lengths = [2, 3, 4]

    def test_cross_matches_dense_pre_softmax_mask_for_both_cfg_orders(self):
        for kinds in ([0, 1], [1, 0]):
            allow = torch.zeros(2, 1, 8, 9, dtype=torch.bool)
            allow[:, :, :, :2] = True
            for b, kind in enumerate(kinds):
                if kind == 0:
                    allow[b, 0, self.groups[0], 2:5] = True
                    allow[b, 0, self.groups[1], 5:9] = True
            expected = F.scaled_dot_product_attention(self.q.transpose(1, 2),
                self.k.transpose(1, 2), self.v.transpose(1, 2), attn_mask=allow
            ).transpose(1, 2).flatten(2)
            actual = r.route_cross(self.q, self.k, self.v, self.groups, self.lengths, kinds)
            torch.testing.assert_close(actual, expected, atol=1e-12, rtol=1e-12)

    def test_foreign_character_text_cannot_change_owned_query_outputs(self):
        a = r.route_cross(self.q, self.k, self.v, self.groups, self.lengths, [0, 1])
        k, v = self.k.clone(), self.v.clone()
        k[:, 5:] *= -100
        v[:, 5:] += 123
        b = r.route_cross(self.q, k, v, self.groups, self.lengths, [0, 1])
        torch.testing.assert_close(a[0, self.groups[0]], b[0, self.groups[0]], atol=0, rtol=0)
        torch.testing.assert_close(a[1], b[1], atol=0, rtol=0)
        self.assertGreater(float((a[0, self.groups[1]] - b[0, self.groups[1]]).abs().max()), 1)

    def test_common_text_still_reaches_both_regions(self):
        a = r.route_cross(self.q, self.k, self.v, self.groups, self.lengths, [0, 1])
        v = self.v.clone()
        v[:, :2] += 5
        b = r.route_cross(self.q, self.k, v, self.groups, self.lengths, [0, 1])
        for indices in self.groups:
            self.assertGreater(float((a[0, indices] - b[0, indices]).abs().max()), 0.1)

    def test_exclusive_ablation_blocks_common_on_positive_only(self):
        a = r.route_cross(self.q, self.k, self.v, self.groups, self.lengths, [0, 1], False)
        v = self.v.clone()
        v[:, :2] += 99
        b = r.route_cross(self.q, self.k, v, self.groups, self.lengths, [0, 1], False)
        torch.testing.assert_close(a[0], b[0], atol=0, rtol=0)
        self.assertGreater(float((a[1] - b[1]).abs().max()), 1)

    def test_self_matches_dense_mask_and_blocks_foreign_values(self):
        q, k, v = self.q, self.k[:, :8], self.v[:, :8]
        allowed = torch.zeros(8, 8, dtype=torch.bool)
        for group in self.groups:
            allowed[group[:, None], group] = True
        expected = F.scaled_dot_product_attention(q.transpose(1, 2), k.transpose(1, 2),
            v.transpose(1, 2), attn_mask=allowed).transpose(1, 2).flatten(2)
        a = r.route_self(q, k, v, self.groups)
        torch.testing.assert_close(a, expected, atol=1e-12, rtol=1e-12)
        v = v.clone()
        v[:, self.groups[1]] += 900
        b = r.route_self(q, k, v, self.groups)
        torch.testing.assert_close(a[:, self.groups[0]], b[:, self.groups[0]], atol=0, rtol=0)

    def test_coordinates_partition_has_five_owners_not_six(self):
        masks = torch.zeros(5, 8, 10)
        for i in range(5):
            masks[i, :, i*2:i*2+2] = 1
        owners = r.token_owners(masks, 4, 10).reshape(4, 10)
        self.assertEqual(owners.unique().tolist(), [0, 1, 2, 3, 4])
        self.assertEqual(owners[0].tolist(), [0, 0, 1, 1, 2, 2, 3, 3, 4, 4])
        reversed_owners = r.token_owners(masks.flip(0), 4, 10)
        torch.testing.assert_close(reversed_owners, 4 - owners.flatten())

    def test_group_priors_are_length_neutral_and_negative_stays_native(self):
        q, k = torch.zeros_like(self.q), torch.zeros_like(self.k)
        v = torch.zeros_like(self.v)
        v[:, :2] = 1
        for common in (.05, 1.):
            result = r.route_cross(q, k, v, self.groups, self.lengths, [0, 1], weights=(common, 1.))
            torch.testing.assert_close(result[0], torch.full_like(result[0], common / (common + 1)))
            torch.testing.assert_close(result[1], torch.ones_like(result[1]))

    def test_weighted_routing_removes_foreign_text_and_positive_padding(self):
        settings = dict(weights=(.05, 1.), common_tokens=1)
        a = r.route_cross(self.q, self.k, self.v, self.groups, self.lengths, [0, 1], **settings)
        k, v = self.k.clone(), self.v.clone()
        k[:, 5:] *= -100
        v[:, 5:] += 123
        v[:, 1] += 55
        b = r.route_cross(self.q, k, v, self.groups, self.lengths, [0, 1], **settings)
        torch.testing.assert_close(a[0, self.groups[0]], b[0, self.groups[0]], atol=0, rtol=0)
        self.assertGreater(float((a[1] - b[1]).abs().max()), 1)

    def test_weak_spatial_prior_retains_cross_region_information(self):
        q, k, v = self.q, self.k[:, :8], self.v[:, :8]
        zero = r.weak_self_bias(self.groups, 8, q, 0)
        torch.testing.assert_close(r.sdpa(q, k, v, zero), r.sdpa(q, k, v))
        bias = r.weak_self_bias(self.groups, 8, q, .2)
        torch.testing.assert_close(bias.exp()[0], q.new_tensor([1, .8, 1, .8, 1, .8, 1, .8]))
        a = r.sdpa(q, k, v, bias)
        v = v.clone()
        v[:, self.groups[1]] += 99
        b = r.sdpa(q, k, v, bias)
        self.assertGreater(float((a[:, self.groups[0]] - b[:, self.groups[0]]).abs().max()), 1)

    def test_schedule_uses_actual_sigma_positions_and_repeated_cfg_evals(self):
        sigmas = [1., .95, .8, .4, .1]
        self.assertEqual([r.sigma_progress(s, sigmas) for s in sigmas], [0., .25, .5, .75, 1.])
        self.assertEqual(r.sigma_progress(.8, sigmas), r.sigma_progress(.8, sigmas))
        self.assertAlmostEqual(r.sigma_progress(.6, sigmas), .625)
        self.assertEqual(r.common_weight(0), .05)
        self.assertEqual(r.common_weight(.4), .05)
        self.assertAlmostEqual(r.common_weight(.575), .525)
        self.assertEqual(r.common_weight(.75), 1.)
        self.assertEqual(r.common_weight(1), 1.)
        with self.assertRaises(ValueError):
            r.sigma_progress(.6, [1, 1, .5])

    def test_uncovered_and_vanished_regions_fail(self):
        with self.assertRaises(ValueError):
            r.token_owners(torch.zeros(2, 4, 4), 2, 2)
        with self.assertRaises(ValueError):
            r.token_owners(torch.ones(2, 4, 4), 2, 2)

    def test_half_initial_common_ramps_to_full_without_changing_timing(self):
        self.assertEqual(r.common_weight(0, .5), .5)
        self.assertEqual(r.common_weight(.4, .5), .5)
        self.assertAlmostEqual(r.common_weight(.575, .5), .75)
        self.assertEqual(r.common_weight(.75, .5), 1.)
        self.assertEqual(r.common_weight(1, .5), 1.)
        for invalid in (-1., 1.01, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                r.common_weight(.5, invalid)

    def test_zero_start_really_blocks_common_and_keeps_negative_native(self):
        for kinds in ([0, 1], [1, 0]):
            positive, negative = kinds.index(0), kinds.index(1)
            settings = dict(weights=(0., 1.), character_gain=1.3)
            a = r.route_cross(self.q, self.k, self.v, self.groups, self.lengths, kinds, **settings)
            expected = r.route_cross(self.q, self.k, self.v, self.groups, self.lengths,
                                     kinds, include_common=False, character_gain=1.3)
            torch.testing.assert_close(a, expected, atol=1e-12, rtol=1e-12)
            k, v = self.k.clone(), self.v.clone()
            k[:, :2] *= -100
            v[:, :2] += 999
            b = r.route_cross(self.q, k, v, self.groups, self.lengths, kinds, **settings)
            torch.testing.assert_close(a[positive], b[positive], atol=0, rtol=0)
            self.assertGreater(float((a[negative] - b[negative]).abs().max()), 1)
            self.assertTrue(torch.isfinite(a).all())
        schedule = [r.common_weight(i / 29, 0.) for i in range(30)]
        self.assertEqual(schedule[:12], [0.] * 12)
        self.assertTrue(all(0. < x < 1. for x in schedule[12:22]))
        self.assertEqual(schedule[22:], [1.] * 8)

    def test_invalid_group_weights_fail(self):
        for weights in ((-1., 1.), (0., 0.), (0., -1.), (float('nan'), 1.), (0., float('inf'))):
            with self.assertRaises(ValueError):
                r.route_cross(self.q, self.k, self.v, self.groups, self.lengths, [0, 1], weights=weights)

    def test_ops_restore_after_error(self):
        originals = [object() for _ in range(4)]
        blocks = [SimpleNamespace(cross_attn=SimpleNamespace(attn_op=originals[i*2]),
                  self_attn=SimpleNamespace(attn_op=originals[i*2+1])) for i in range(2)]
        replacement = object()
        with self.assertRaisesRegex(RuntimeError, "cancelled"):
            with r.installed_ops(blocks, replacement, replacement):
                self.assertIs(blocks[1].self_attn.attn_op, replacement)
                raise RuntimeError("cancelled")
        for i, block in enumerate(blocks):
            self.assertIs(block.cross_attn.attn_op, originals[i*2])
            self.assertIs(block.self_attn.attn_op, originals[i*2+1])

    def test_value_gain_preserves_common_and_negative_with_analytic_outputs(self):
        q, k = torch.zeros_like(self.q), torch.zeros_like(self.k)
        v = torch.full_like(self.v, 4.)
        v[:, :2] = 2.
        for kinds in ([0, 1], [1, 0]):
            for gain in (1., 1.3, 1.5, 1.7, 2.):
                result = r.route_cross(q, k, v, self.groups, self.lengths, kinds,
                                       weights=(.3, 1.), character_gain=gain)
                for batch, kind in enumerate(kinds):
                    expected = 2. if kind == 1 else (.3 * 2. + gain * 4.) / 1.3
                    torch.testing.assert_close(result[batch], torch.full_like(result[batch], expected))

    def test_value_gain_matches_explicit_dense_attention_and_preserves_inputs(self):
        original_v = self.v.clone()
        for kinds in ([0, 1], [1, 0]):
            bias = torch.full((2, 1, 8, 9), -torch.inf, dtype=self.q.dtype)
            v = self.v.clone()
            for b, kind in enumerate(kinds):
                bias[b, 0, :, :2] = 0. if kind == 1 else r.math.log(.3 / 2)
                if kind == 0:
                    v[b, 2:] *= 2.
                    for i, (lo, hi) in enumerate(((2, 5), (5, 9))):
                        bias[b, 0, self.groups[i], lo:hi] = r.math.log(1. / (hi - lo))
            expected = F.scaled_dot_product_attention(self.q.transpose(1, 2),
                self.k.transpose(1, 2), v.transpose(1, 2), attn_mask=bias).transpose(1, 2).flatten(2)
            actual = r.route_cross(self.q, self.k, self.v, self.groups, self.lengths, kinds,
                                   weights=(.3, 1.), character_gain=2.)
            torch.testing.assert_close(actual, expected, atol=1e-12, rtol=1e-12)
        torch.testing.assert_close(original_v, self.v, atol=0, rtol=0)

    def test_gain_schedule_starts_strong_and_returns_to_baseline(self):
        for p, expected in zip((0., .4, .575, .75, 1.), (2., 2., 1.5, 1., 1.)):
            self.assertAlmostEqual(r.character_value_gain(p, 2.), expected)
        for p in (0., .4, .6, .75, 1.):
            self.assertEqual(r.character_value_gain(p), 1.)
        for bad in (0., -1., 3.1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                r.character_value_gain(.5, bad)
            with self.assertRaises(ValueError):
                r.route_cross(self.q, self.k, self.v, self.groups, self.lengths, [0, 1], character_gain=bad)
        for bad in (-.1, 1.1, float('nan')):
            with self.assertRaises(ValueError):
                r.character_value_gain(bad, 2.)

    def test_strict_then_relaxed_spatial_schedule_and_actual_attention(self):
        for p, expected in zip((0., .4, .575, .75, 1.), (.9, .9, .55, .2, .2)):
            separation = r.spatial_separation(p, .9, .2)
            self.assertAlmostEqual(separation, expected)
            # Uniform QK, equal regions: analytically known contribution.
            q = torch.zeros_like(self.q)
            v = torch.zeros_like(q)
            v[:, self.groups[1]] = 1.
            bias = r.weak_self_bias(self.groups, 8, q, separation)
            actual = r.sdpa(q, q, v, bias)
            foreign = (1 - expected) / (2 - expected)
            torch.testing.assert_close(actual[:, self.groups[0]], torch.full_like(actual[:, self.groups[0]], foreign))
            torch.testing.assert_close(actual[:, self.groups[1]], torch.full_like(actual[:, self.groups[1]], 1 - foreign))
        schedule = [r.spatial_separation(i/29, .9, .2) for i in range(30)]
        self.assertEqual(schedule[:12], [.9]*12)
        self.assertTrue(all(a >= b for a, b in zip(schedule, schedule[1:])))
        for p in (0., .4, .6, .75, 1.):
            self.assertEqual(r.spatial_separation(p), .2)
        for bad in (-.1, 1., float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                r.spatial_separation(.5, bad, .2)
            with self.assertRaises(ValueError):
                r.spatial_separation(.5, .9, bad)

    def test_double_decrement_on_actual_sigmas_opens_from_step16(self):
        expected = [.9]*3 + [.7]*3 + [.5]*3 + [.3]*3 + [.1]*3 + [0.]*15
        for sigmas in ([1. - i / 31 for i in range(30)],
                       [1. / (i + 1) for i in range(30)]):
            for i, sigma in enumerate(sigmas):
                p = r.sigma_progress(sigma, sigmas)
                for _ in range(2):
                    sep = r.stepped_spatial_separation(p, 30, .9, .2)
                    self.assertAlmostEqual(sep, expected[i])
                    bias = r.weak_self_bias(self.groups, 8, self.q, sep)
                    if i >= 15:
                        self.assertEqual(int(torch.count_nonzero(bias)), 0)
                    else:
                        self.assertLess(float(bias[0, 1]), 0.)
        self.assertEqual(r.stepped_spatial_separation(2.999 / 29, 30, .9, .2), .9)
        self.assertAlmostEqual(r.stepped_spatial_separation(3. / 29, 30, .9, .2), .7)
        for bad in (0., -.1, 1.1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                r.stepped_spatial_separation(.5, 30, .9, bad)

    def test_double_common_increment_reaches_full_at_step16_without_changing_boundary(self):
        expected = [0.]*3 + [.2]*3 + [.4]*3 + [.6]*3 + [.8]*3 + [1.]*15
        q, k = torch.zeros_like(self.q), torch.zeros_like(self.k)
        v = torch.full_like(self.v, 4.)
        v[:, :2] = 2.
        for sigmas in ([1. - i / 31 for i in range(30)],
                       [1. / (i + 1) for i in range(30)]):
            for i, sigma in enumerate(sigmas):
                p = r.sigma_progress(sigma, sigmas)
                for _ in range(2):
                    weight = r.stepped_common_weight(p, 30, 0., .2)
                    self.assertAlmostEqual(weight, expected[i])
                    self.assertEqual(r.stepped_common_weight(p, 30), (i // 3) / 10.)
                    self.assertAlmostEqual(r.stepped_spatial_separation(p, 30, .9, .2),
                                           max(0., .9 - .2 * (i // 3)))
                    actual = r.route_cross(q, k, v, self.groups, self.lengths, [0, 1],
                                           weights=(weight, 1.))
                    positive = (weight * 2. + 4.) / (weight + 1.)
                    torch.testing.assert_close(actual[0], torch.full_like(actual[0], positive))
                    torch.testing.assert_close(actual[1], torch.full_like(actual[1], 2.))
        self.assertEqual(r.stepped_common_weight(2.999 / 29, 30, 0., .2), 0.)
        self.assertAlmostEqual(r.stepped_common_weight(3. / 29, 30, 0., .2), .2)
        self.assertEqual(r.stepped_common_weight(1., 30, .5, .2), 1.)
        for bad in (0., -.1, 1.1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                r.stepped_common_weight(.5, 30, 0., bad)

    def test_triple_decrement_releases_bias_exactly_at_step10(self):
        expected = [.9] * 3 + [.6] * 3 + [.3] * 3 + [0.] * 21
        q = self.q
        k, v = torch.randn_like(q), torch.randn_like(q)
        for sigmas in ([1. - i / 31 for i in range(30)],
                       [1. / (i + 1) for i in range(30)]):
            for i, sigma in enumerate(sigmas):
                p = r.sigma_progress(sigma, sigmas)
                sep = r.stepped_spatial_separation(p, 30, .9, .3)
                self.assertAlmostEqual(sep, expected[i])
                bias = r.weak_self_bias(self.groups, 8, q, sep)
                if i >= 9:
                    self.assertEqual(sep, 0.)
                    self.assertEqual(int(torch.count_nonzero(bias)), 0)
                    torch.testing.assert_close(r.sdpa(q, k, v, bias), r.sdpa(q, k, v), atol=1e-12, rtol=1e-12)
                else:
                    self.assertLess(float(bias[0, 1]), 0.)
                self.assertAlmostEqual(r.stepped_common_weight(p, 30, 0., .2), min(1., .2 * (i // 3)))

    def test_hold2_decay_opens_at_step5_without_advancing_on_cfg_calls(self):
        q, k, v = self.q, torch.randn_like(self.q), torch.randn_like(self.q)
        expected = [.9, .9, .5, .1] + [0.] * 26
        for sigmas in ([1. - i / 31 for i in range(30)],
                       [1. / (i + 1) for i in range(30)]):
            for i, sigma in enumerate(sigmas):
                for _ in range(2):
                    p = r.sigma_progress(sigma, sigmas)
                    sep = r.hold2_decay_spatial_separation(p, len(sigmas))
                    self.assertAlmostEqual(sep, expected[i])
                    bias = r.weak_self_bias(self.groups, 8, q, sep)
                    actual = r.sdpa(q, k, v, bias)
                    if i >= 4:
                        self.assertEqual(int(torch.count_nonzero(bias)), 0)
                        torch.testing.assert_close(actual, r.sdpa(q, k, v), atol=1e-12, rtol=1e-12)
                    else:
                        self.assertGreater(float((actual-r.sdpa(q, k, v)).abs().max()), .001)
        for bad in (0, 1, 30., True):
            with self.assertRaises(ValueError):
                r.hold2_decay_spatial_separation(.5, bad)
        for bad in (0., -.1, 1.1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                r.hold2_decay_spatial_separation(.5, 30, decrement=bad)
        for bad in (-.1, 1.1, float('nan')):
            with self.assertRaises(ValueError):
                r.hold2_decay_spatial_separation(bad, 30)

    def test_release_step2_opens_self_attention_at_second_sigma(self):
        q = self.q
        k, v = torch.randn_like(q), torch.randn_like(q)
        for sigmas in ([1. - i / 31 for i in range(30)],
                       [1. / (i + 1) for i in range(30)]):
            for i, sigma in enumerate(sigmas):
                for _ in range(2):
                    p = r.sigma_progress(sigma, sigmas)
                    sep = r.release_step2_spatial_separation(p, len(sigmas))
                    self.assertEqual(sep, .9 if i == 0 else 0.)
                    bias = r.weak_self_bias(self.groups, 8, q, sep)
                    actual = r.sdpa(q, k, v, bias)
                    unmasked = r.sdpa(q, k, v)
                    if i == 0:
                        self.assertGreater(float((actual - unmasked).abs().max()), .01)
                    else:
                        self.assertEqual(int(torch.count_nonzero(bias)), 0)
                        torch.testing.assert_close(actual, unmasked, atol=1e-12, rtol=1e-12)
                        # A foreign region's value now reaches the owned queries.
                        changed_v = v.clone()
                        changed_v[:, self.groups[1]] += 20
                        changed = r.sdpa(q, k, changed_v, bias)
                        self.assertGreater(float((actual[:, self.groups[0]] - changed[:, self.groups[0]]).abs().max()), 1.)
        self.assertEqual(r.release_step2_spatial_separation(.999 / 29, 30), .9)
        self.assertEqual(r.release_step2_spatial_separation(1. / 29, 30), 0.)
        for bad in (1, 0, 30.5, True):
            with self.assertRaises(ValueError):
                r.release_step2_spatial_separation(.5, bad)
        for bad in (-.1, 1.1, float('nan')):
            with self.assertRaises(ValueError):
                r.release_step2_spatial_separation(bad, 30)

    def test_parametric_hold_decay_preserves_legacy_and_controls_foreign_values(self):
        q = torch.zeros_like(self.q)
        v = torch.zeros_like(q)
        v[:, self.groups[1]] = 1.
        for sigmas in ([1. - i / 31 for i in range(30)], [1. / (i + 1) for i in range(30)]):
            for i, sigma in enumerate(sigmas):
                p = r.sigma_progress(sigma, sigmas)
                self.assertEqual(r.hold_decay_spatial_separation(p, 30, hold_steps=2, decrement=.4),
                                 r.hold2_decay_spatial_separation(p, 30))
                for hold, dec in ((2, .2), (3, .2), (3, .3)):
                    sep = r.hold_decay_spatial_separation(p, 30, hold_steps=hold, decrement=dec)
                    self.assertEqual(sep, r.hold_decay_spatial_separation(p, 30, hold_steps=hold, decrement=dec))
                    if i < hold:
                        self.assertEqual(sep, .9)
                    bias = r.weak_self_bias(self.groups, 8, q, sep)
                    actual = r.sdpa(q, q, v, bias)
                    expected_foreign_share = (1 - sep) / (2 - sep)
                    torch.testing.assert_close(actual[:, self.groups[0]], torch.full_like(actual[:, self.groups[0]], expected_foreign_share))
                    if sep == 0:
                        torch.testing.assert_close(actual, r.sdpa(q, q, v), atol=0, rtol=0)
        self.assertAlmostEqual(r.hold_decay_spatial_separation(3/29, 30, hold_steps=3, decrement=.2), .7)
        for kwargs in ({'hold_steps': 0}, {'hold_steps': True}, {'hold_steps': 31},
                       {'hold_steps': 2.5}, {'decrement': 0}, {'decrement': float('nan')},
                       {'decrement': 1.1}):
            with self.assertRaises(ValueError):
                r.hold_decay_spatial_separation(.5, 30, **kwargs)

    def test_post_step3_common_boost_preserves_prefix_and_actual_attention(self):
        q, k, v = torch.zeros_like(self.q), torch.zeros_like(self.k), torch.zeros_like(self.v)
        v[:, :2] = 1.
        for sigmas in ([1. - i / 31 for i in range(30)], [1. / (i + 1) for i in range(30)]):
            for i, sigma in enumerate(sigmas):
                p = r.sigma_progress(sigma, sigmas)
                base = r.stepped_common_weight(p, 30, .05, .2)
                for boost in (0., .1, .2):
                    actual = r.stepped_common_weight(p, 30, .05, .2, boost)
                    self.assertAlmostEqual(actual, min(1., .05 + (i // 3) * .2 + (boost if i >= 3 else 0.)))
                    self.assertEqual(actual, r.stepped_common_weight(p, 30, .05, .2, boost))
                    if i < 3 or boost == 0.:
                        self.assertEqual(actual, base)
                    out = r.route_cross(q, k, v, self.groups, self.lengths, [0, 1], weights=(actual, 1.))
                    # With equal logits, normalized group weights have this analytic share.
                    torch.testing.assert_close(out[0], torch.full_like(out[0], actual / (actual + 1.)))
                    torch.testing.assert_close(out[1], torch.ones_like(out[1]))
        for bad in (-.1, 1.1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                r.stepped_common_weight(.5, 30, .05, .2, bad)

    def test_staged_gain_boundaries_and_thirty_evaluations(self):
        self.assertEqual([r.staged_character_gain(p) for p in (0., .399, .4, .749, .75, 1.)],
                         [1.3, 1.3, 1.5, 1.5, 1.7, 1.7])
        self.assertEqual([r.staged_character_gain(i / 29) for i in range(30)],
                         [1.3] * 12 + [1.5] * 10 + [1.7] * 8)
        for bad in (0., -1., 3.1, float('nan'), float('inf')):
            for slot in range(3):
                values = [1.3, 1.5, 1.7]
                values[slot] = bad
                with self.assertRaises(ValueError):
                    r.staged_character_gain(.5, *values)
        for bad in (-.1, 1.1, float('nan')):
            with self.assertRaises(ValueError):
                r.staged_character_gain(bad)

    def test_staged_gain_on_different_sigma_spacings(self):
        for sigmas in ([1. - i / 31 for i in range(30)],
                       [1. / (i + 1) for i in range(30)]):
            gains = [r.staged_character_gain(r.sigma_progress(s, sigmas)) for s in sigmas]
            self.assertEqual(gains, [1.3] * 12 + [1.5] * 10 + [1.7] * 8)

    def test_stepped_common_schedule_and_actual_attention(self):
        # Both schedule spacing and repeated CFG calls must be irrelevant.
        q, k = torch.zeros_like(self.q), torch.zeros_like(self.k)
        v = torch.full_like(self.v, 4.)
        v[:, :2] = 2.
        expected_weights = [i / 10. for i in range(10) for _ in range(3)]
        for sigmas in ([1. - i / 31 for i in range(30)],
                       [1. / (i + 1) for i in range(30)]):
            for i, sigma in enumerate(sigmas):
                for _ in range(2):
                    p = r.sigma_progress(sigma, sigmas)
                    weight = r.stepped_common_weight(p, len(sigmas))
                    self.assertEqual(weight, expected_weights[i])
                    result = r.route_cross(q, k, v, self.groups, self.lengths,
                                           [0, 1], weights=(weight, 1.))
                    expected = (weight * 2. + 4.) / (weight + 1.)
                    torch.testing.assert_close(result[0], torch.full_like(result[0], expected))
                    torch.testing.assert_close(result[1], torch.full_like(result[1], 2.))
        self.assertEqual(r.stepped_common_weight(2.999 / 29., 30), 0.)
        self.assertEqual(r.stepped_common_weight(3. / 29., 30), .1)
        self.assertEqual(r.stepped_common_weight(1., 33), 1.)
        for bad in (-.1, 1.1, float('nan')):
            with self.assertRaises(ValueError):
                r.stepped_common_weight(bad, 30)
        for bad in (1, 0, 30.5, True):
            with self.assertRaises(ValueError):
                r.stepped_common_weight(.5, bad)


    def test_stepped_separation_attention_boundaries_and_full_release(self):
        # Check actual attention, not just a duplicated schedule formula.
        q = torch.zeros_like(self.q)
        v = torch.zeros_like(q)
        v[:, self.groups[1]] = 1.
        for sigmas in ([1. - i / 31 for i in range(30)],
                       [1. / (i + 1) for i in range(30)]):
            for i, sigma in enumerate(sigmas):
                p = r.sigma_progress(sigma, sigmas)
                separation = r.stepped_spatial_separation(p, len(sigmas))
                self.assertAlmostEqual(separation, (9 - i // 3) / 10)
                self.assertEqual(separation, r.stepped_spatial_separation(p, len(sigmas)))
                bias = r.weak_self_bias(self.groups, 8, q, separation)
                actual = r.sdpa(q, q, v, bias)
                expected = (1 - separation) / (2 - separation)
                torch.testing.assert_close(actual[:, self.groups[0]], torch.full_like(actual[:, self.groups[0]], expected))
                if i >= 27:
                    torch.testing.assert_close(actual, r.sdpa(q, q, v), atol=0, rtol=0)
        self.assertEqual(r.stepped_spatial_separation(2.999 / 29, 30), .9)
        self.assertAlmostEqual(r.stepped_spatial_separation(3. / 29, 30), .8)
        self.assertEqual(r.stepped_spatial_separation(1., 33), 0.)
        for bad in (-.1, 1., float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                r.stepped_spatial_separation(.5, 30, bad)
        for bad in (-.1, 1.1, float("nan")):
            with self.assertRaises(ValueError):
                r.stepped_spatial_separation(bad, 30)
        for bad in (0, 1, 30.5, True):
            with self.assertRaises(ValueError):
                r.stepped_spatial_separation(.5, bad)


if __name__ == "__main__":
    unittest.main()
