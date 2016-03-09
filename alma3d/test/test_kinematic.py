# -*- coding: utf-8 -*-

from alma3d.Kinematic import Kinematic
import unittest


class TestKinematic(unittest.TestCase):
    '''Test per il controllo della cinematica

    Devo inserire un controllo per l'orientamento degli assi

    [ZYX]                 [XYZ]                 [Steps]
    (Roll, Pitch, Yaw) -> (Roll, Pitch, Yaw) -> (Step_119, Step_120, Step_121, Step_122) -> (Roll, Pitch, Yaw) -> (Roll, Pitch, Yaw)

    Ho preso dall'ultimo file excel i seguenti punti:

    ZYX                XYZ                Steps                           H relative
    Roll  Pitch Yaw    Roll  Pitch Yaw    M_120   M_121   M_122   M_119   H_121  H_122  H_123
      0,0   0,0   0,0    0,0   0,0   0,0        0       0       0      0   0,000  0,000  0,000
     20,0   0,0   0,0   20,0   0,0   0,0      165 -167155  166825      7   0,000  0,209 -0,209
    -20,0   0,0   0,0  -20,0   0,0   0,0      165  166825 -167155    -16   0,000 -0,209  0,209
      0,0  20,0   0,0    0,0  20,0   0,0  -145105  145105  145105    -10   0,181 -0,181 -0,181
      0,0 -20,0   0,0    0,0 -20,0   0,0   144126 -144126 -144126     -9  -0,180  0,180  0,180
      0,0   0,0  20,0    0,0   0,0  20,0        0       0       0 -51111   0,000  0,000  0,000
      0,0   0,0 -20,0    0,0   0,0 -20,0        0       0       0  51111   0,000  0,000  0,000
     20,0  20,0   0,0   21,2  18,7 -07,1  -143910  -11303  299123   9115   0,180  0,014 -0,374
     20,0 -20,0   0,0   21,2 -18,7  07,1   145037 -303053   12979  -9097  -0,181  0,379 -0,016
    -20,0  20,0   0,0  -21,2  18,7  07,1  -143910  299120  -11301  -9126   0,180 -0,374  0,014
    -20,0 -20,0   0,0  -21,2 -18,7 -07,1   145035   12981 -303050   9076  -0,181 -0,016  0,379
     20,0  20,0  20,0   13,5  24,8  13,5  -143910  -11303  299123 -41996   0,180  0,014 -0,374
     20,0 -20,0  20,0   26,0 -10,7  26,0   145037 -303053   12979 -60208  -0,181  0,379 -0,016
    -20,0  20,0  20,0  -26,0  10,7  26,0  -143910  299120  -11301 -60237   0,180 -0,374  0,014
    -20,0 -20,0  20,0  -13,5 -24,8  13,5   145035   12981 -303050 -42036  -0,181 -0,016  0,379
     20,0  20,0 -20,0   26,0  10,7 -26,0  -143910  -11303  299123  60226   0,180  0,014 -0,374
     20,0 -20,0 -20,0   13,5 -24,8 -13,5   145037 -303053   12979  42014  -0,181  0,379 -0,016
    -20,0  20,0 -20,0  -13,5  24,8 -13,5  -143910  299120  -11301  41986   0,180 -0,374  0,014
    -20,0 -20,0 -20,0  -26,0 -10,7 -26,0   145035   12981 -303050  60187  -0,181 -0,016  0,379

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
