# -*- coding: utf-8 -*-

from alma3d.Kinematic import Kinematic
import unittest


class TestKinematic(unittest.TestCase):
    '''Test per il controllo della cinematica

    Devo inserire un controllo per l'orientamento degli assi

    (Roll, Pitch, Yaw) -> (Roll, Pitch, Yaw) -> (Step_119, Step_120, Step_121, Step_122) -> (Roll, Pitch, Yaw) -> (Roll, Pitch, Yaw)

    '''

    real_height = 1.685

    def __init__(self, methodName):

        unittest.TestCase.__init__(self, methodName)
        self.k = Kinematic()

    def test_distance_12(self):
        alphas = [0.010368433, -0.00822037, 0.039655526]
        motor_positions = [self.real_height + 0.2, self.real_height + 0.1, self.real_height - 0.2]
        distance_12 = self.k.distance_12(alphas, motor_positions)
        self.assertAlmostEqual(distance_12, 1.22110008246315, 5)

    def test_distance_23(self):
        alphas = [0.010368433, -0.00822037, 0.039655526]
        motor_positions = [self.real_height + 0.2, self.real_height + 0.1, self.real_height - 0.2]
        distance_23 = self.k.distance_23(alphas, motor_positions)
        self.assertAlmostEqual(distance_23, 1.22110001840372, 5)

    def test_distance_13(self):
        alphas = [0.010368433, -0.00822037, 0.039655526]
        motor_positions = [self.real_height + 0.2, self.real_height + 0.1, self.real_height - 0.2]
        distance_13 = self.k.distance_13(alphas, motor_positions)
        self.assertAlmostEqual(distance_13, 1.22109991986487, 5)

    def test_find_solution(self):
        self.k.find_solution([+0.0000, +0.0533, -0.0533, 0.000])
        self.assertAlmostEqual(self.k.zyx3, 5.0086, 2)
        self.assertAlmostEqual(self.k.zyx2, 0.0001, 2)
        self.assertAlmostEqual(self.k.zyx1, 0.0062, 2)
        self.k.find_solution([+0.0000, +0.1060, -0.1060, +0.0000])
        self.assertAlmostEqual(self.k.zyx3, 9.9993, 2)
        self.assertAlmostEqual(self.k.zyx2, 0.0014, 2)
        self.assertAlmostEqual(self.k.zyx1, 0.0008, 2)
        self.k.find_solution([+0.0461, -0.0461, -0.0461, +0.0000])
        self.assertAlmostEqual(self.k.zyx3, 0.0000, 2)
        self.assertAlmostEqual(self.k.zyx2, 5.0014, 2)
        self.assertAlmostEqual(self.k.zyx1, 0.0057, 2)
        self.k.find_solution([+0.0919, -0.0919, -0.0919, +0.0000])
        self.assertAlmostEqual(self.k.zyx3, 0.0000, 2)
        self.assertAlmostEqual(self.k.zyx2, 10.0051, 2)
        self.assertAlmostEqual(self.k.zyx1, 0.0057, 2)
        self.k.find_solution([+0.0461, +0.0069, -0.0991, +0.0000])
        self.assertAlmostEqual(self.k.zyx3, 5.0003, 2)
        self.assertAlmostEqual(self.k.zyx2, 5.0027, 2)
        self.assertAlmostEqual(self.k.zyx1, -0.2187, 2)
        self.k.find_solution([+0.0918, +0.0125, -0.1960, +0.0000])
        self.assertAlmostEqual(self.k.zyx3, 9.9981, 2)
        self.assertAlmostEqual(self.k.zyx2, 10.0024, 2)
        self.assertAlmostEqual(self.k.zyx1, -0.8742, 2)
        self.k.find_solution([+0.0000, +0.0533, -0.0533, +1.5860])
        self.assertAlmostEqual(self.k.zyx3, 5.0086, 2)
        self.assertAlmostEqual(self.k.zyx2, 0.0001, 2)
        self.assertAlmostEqual(self.k.zyx1, 90.8758, 2)
        self.k.find_solution([+0.0000, +0.1060, -0.1060, +1.5860])
        self.assertAlmostEqual(self.k.zyx3, 9.9993, 2)
        self.assertAlmostEqual(self.k.zyx2, 0.0014, 2)
        self.assertAlmostEqual(self.k.zyx1, 90.8719, 2)
        self.k.find_solution([+0.0461, -0.0461, -0.0461, +1.5860])
        self.assertAlmostEqual(self.k.zyx3, 0.0000, 2)
        self.assertAlmostEqual(self.k.zyx2, 5.0014, 2)
        self.assertAlmostEqual(self.k.zyx1, 90.8768, 2)
        self.k.find_solution([+0.0919, -0.0919, -0.0919, +1.5860])
        self.assertAlmostEqual(self.k.zyx3, 0.0000, 2)
        self.assertAlmostEqual(self.k.zyx2, 10.0051, 2)
        self.assertAlmostEqual(self.k.zyx1, 90.8768, 2)
        self.k.find_solution([+0.0461, +0.0069, -0.0991, +1.5860])
        self.assertAlmostEqual(self.k.zyx3, 5.0003, 2)
        self.assertAlmostEqual(self.k.zyx2, 5.0027, 2)
        self.assertAlmostEqual(self.k.zyx1, 90.6524, 2)
        self.k.find_solution([+0.0918, +0.0125, -0.1960, +1.5860])
        self.assertAlmostEqual(self.k.zyx3, 9.9981, 2)
        self.assertAlmostEqual(self.k.zyx2, 10.0024, 2)
        self.assertAlmostEqual(self.k.zyx1, 89.9969, 2)

    def test_find_solution_fast(self):
        self.k.find_solution_fast([+0.0000, +0.0533, -0.0533, 0.000])
        self.assertAlmostEqual(self.k.zyx3, 5.0086, 2)
        self.assertAlmostEqual(self.k.zyx2, 0.0001, 2)
        self.assertAlmostEqual(self.k.zyx1, 0.0062, 2)
        self.k.find_solution_fast([+0.0000, +0.1060, -0.1060, +0.0000])
        self.assertAlmostEqual(self.k.zyx3, 9.9993, 2)
        self.assertAlmostEqual(self.k.zyx2, 0.0014, 2)
        self.assertAlmostEqual(self.k.zyx1, 0.0008, 2)
        self.k.find_solution_fast([+0.0461, -0.0461, -0.0461, +0.0000])
        self.assertAlmostEqual(self.k.zyx3, 0.0000, 2)
        self.assertAlmostEqual(self.k.zyx2, 5.0014, 2)
        self.assertAlmostEqual(self.k.zyx1, 0.0057, 2)
        self.k.find_solution_fast([+0.0919, -0.0919, -0.0919, +0.0000])
        self.assertAlmostEqual(self.k.zyx3, 0.0000, 2)
        self.assertAlmostEqual(self.k.zyx2, 10.0051, 2)
        self.assertAlmostEqual(self.k.zyx1, 0.0057, 2)
        self.k.find_solution_fast([+0.0461, +0.0069, -0.0991, +0.0000])
        self.assertAlmostEqual(self.k.zyx3, 5.0003, 2)
        self.assertAlmostEqual(self.k.zyx2, 5.0027, 2)
        self.assertAlmostEqual(self.k.zyx1, -0.2187, 2)
        self.k.find_solution_fast([+0.0918, +0.0125, -0.1960, +0.0000])
        self.assertAlmostEqual(self.k.zyx3, 9.9981, 2)
        self.assertAlmostEqual(self.k.zyx2, 10.0024, 2)
        self.assertAlmostEqual(self.k.zyx1, -0.8742, 2)
        self.k.find_solution_fast([+0.0000, +0.0533, -0.0533, +1.5860])
        self.assertAlmostEqual(self.k.zyx3, 5.0086, 2)
        self.assertAlmostEqual(self.k.zyx2, 0.0001, 2)
        self.assertAlmostEqual(self.k.zyx1, 90.8758, 2)
        self.k.find_solution_fast([+0.0000, +0.1060, -0.1060, +1.5860])
        self.assertAlmostEqual(self.k.zyx3, 9.9993, 2)
        self.assertAlmostEqual(self.k.zyx2, 0.0014, 2)
        self.assertAlmostEqual(self.k.zyx1, 90.8719, 2)
        self.k.find_solution_fast([+0.0461, -0.0461, -0.0461, +1.5860])
        self.assertAlmostEqual(self.k.zyx3, 0.0000, 2)
        self.assertAlmostEqual(self.k.zyx2, 5.0014, 2)
        self.assertAlmostEqual(self.k.zyx1, 90.8768, 2)
        self.k.find_solution_fast([+0.0919, -0.0919, -0.0919, +1.5860])
        self.assertAlmostEqual(self.k.zyx3, 0.0000, 2)
        self.assertAlmostEqual(self.k.zyx2, 10.0051, 2)
        self.assertAlmostEqual(self.k.zyx1, 90.8768, 2)
        self.k.find_solution_fast([+0.0461, +0.0069, -0.0991, +1.5860])
        self.assertAlmostEqual(self.k.zyx3, 5.0003, 2)
        self.assertAlmostEqual(self.k.zyx2, 5.0027, 2)
        self.assertAlmostEqual(self.k.zyx1, 90.6524, 2)
        self.k.find_solution_fast([+0.0918, +0.0125, -0.1960, +1.5860])
        self.assertAlmostEqual(self.k.zyx3, 9.9981, 2)
        self.assertAlmostEqual(self.k.zyx2, 10.0024, 2)
        self.assertAlmostEqual(self.k.zyx1, 89.9969, 2)

if __name__ == '__main__':
    unittest.main()
