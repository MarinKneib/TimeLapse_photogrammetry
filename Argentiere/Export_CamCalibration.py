import Metashape

doc = Metashape.app.document
export_dir  = "X:/Partage/argentiere_courtes_270923/"

for chunk in doc.chunks:
    for camera in chunk.cameras:
        filename = ''.join([export_dir,'CAMCalib_',camera.label,'.txt'])
        if camera.calibration:
            camera.calibration.save(filename, format = Metashape.CalibrationFormatAustralis)
print("Script finished")

