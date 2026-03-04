clear
close all

cd 'Z:\gl_kneibm\Projects\PI\2024_CAIRN-GLOBAL\TL_photogrammetry_Argentiere\code'

image_dir = 'Z:\gl_kneibm\Projects\PI\2024_CAIRN-GLOBAL\TL_photogrammetry_Argentiere\data\TLCAM\Images\';
results_dir = 'Z:\gl_kneibm\Projects\PI\2024_CAIRN-GLOBAL\TL_photogrammetry_Argentiere\data\TLCAM\CAM_selection\';

% image lists 
CAM1_images = dir([image_dir,'CAM1\*.JPG']);
CAM2B_images = dir([image_dir,'CAM2B\*.JPG']);
CAM2N_images = dir([image_dir,'CAM2N\*.JPG']);
CAM3_images = dir([image_dir,'CAM3\*.JPG']);
CAM4B_images = dir([image_dir,'CAM4B\*.JPG']);
CAM4N_images = dir([image_dir,'CAM4N\*.JPG']);
CAM4QUALI_images = dir([image_dir,'CAM4QUALI\*.JPG']);
CAM5_images = dir([image_dir,'CAM5\*.JPG']);

% extract dates of each camera images
date1 = [];
date2B = [];
date2N = [];
date3 = [];
date4B = [];
date4N = [];
date4Q = [];
date5 = [];

for ii = 1:length(CAM1_images)
    date_str = CAM1_images(ii).name(6:22);
    date1 = [date1; datetime(date_str,'InputFormat','yyyy-MM-dd_HHmmss')];
end
for ii = 1:length(CAM2B_images)
    date_str = CAM2B_images(ii).name(7:23);
    date2B = [date2B; datetime(date_str,'InputFormat','yyyy-MM-dd_HHmmss')];
end
for ii = 1:length(CAM2N_images)
    date_str = CAM2N_images(ii).name(7:23);
    date2N = [date2N; datetime(date_str,'InputFormat','yyyy-MM-dd_HHmmss')];
end
for ii = 1:length(CAM3_images)
    date_str = CAM3_images(ii).name(6:22);
    date3 = [date3; datetime(date_str,'InputFormat','yyyy-MM-dd_HHmmss')];
end
for ii = 1:length(CAM4N_images)
    date_str = CAM4N_images(ii).name(7:23);
    date4N = [date4N; datetime(date_str,'InputFormat','yyyy-MM-dd_HHmmss')];
end
for ii = 1:length(CAM4B_images)
    date_str = CAM4B_images(ii).name(7:23);
    date4B = [date4B; datetime(date_str,'InputFormat','yyyy-MM-dd_HHmmss')];
end
for ii = 1:length(CAM4QUALI_images)
    date_str = CAM4QUALI_images(ii).name(11:27);
    date4Q = [date4Q; datetime(date_str,'InputFormat','yyyy-MM-dd_HHmmss')];
end
for ii = 1:length(CAM5_images)
    date_str = CAM5_images(ii).name(6:22);
    date5 = [date5; datetime(date_str,'InputFormat','yyyy-MM-dd_HHmmss')];
end

% remove CAM1 images before 01/08/2023
CAM1_images = CAM1_images(date1>datetime(2023,08,01));
date1 = date1(date1>datetime(2023,08,01));

% initialize table
cellarray = cell(length(date1), 8);
Table = cell2table(cellarray,'VariableNames',{'CAM1', 'CAM2N', 'CAM2B', 'CAM3', 'CAM4N', ...
                              'CAM4B', 'CAM5', 'CAM4QUALI'});

% fill table with image names using CAM1 as reference
for ii = 1:length(date1)
    Table.CAM1{ii} = CAM1_images(ii).name;
    % for each other camera find the closest image within +/- 2 hours
    date2N_tmp = date2N(date2N>date1(ii)-hours(2) & date2N<date1(ii)+hours(2));
    if ~isempty(date2N_tmp)
        [~, minIndex] = min(abs(date2N-date1(ii)));
        Table.CAM2N{ii} = CAM2N_images(minIndex).name;
    else
        Table.CAM2N{ii} = '.'; % fill with '.' when no image is available
    end
    date2B_tmp = date2B(date2B>date1(ii)-hours(2) & date2B<date1(ii)+hours(2));
    if ~isempty(date2B_tmp)
        [~, minIndex] = min(abs(date2B-date1(ii)));
        Table.CAM2B{ii} = CAM2B_images(minIndex).name;
    else
        Table.CAM2B{ii} = '.'; % fill with '.' when no image is available
    end
    date3_tmp = date3(date3>date1(ii)-hours(2) & date3<date1(ii)+hours(2));
    if ~isempty(date3_tmp)
        [~, minIndex] = min(abs(date3-date1(ii)));
        Table.CAM3{ii} = CAM3_images(minIndex).name;
    else
        Table.CAM3{ii} = '.'; % fill with '.' when no image is available
    end
    date4N_tmp = date4N(date4N>date1(ii)-hours(2) & date4N<date1(ii)+hours(2));
    if ~isempty(date4N_tmp)
        [~, minIndex] = min(abs(date4N-date1(ii)));
        Table.CAM4N{ii} = CAM4N_images(minIndex).name;
    else
        Table.CAM4N{ii} = '.'; % fill with '.' when no image is available
    end
    date4B_tmp = date4B(date4B>date1(ii)-hours(2) & date4B<date1(ii)+hours(2));
    if ~isempty(date4B_tmp)
        [~, minIndex] = min(abs(date4B-date1(ii)));
        Table.CAM4B{ii} = CAM4B_images(minIndex).name;
    else
        Table.CAM4B{ii} = '.'; % fill with '.' when no image is available
    end
    date4Q_tmp = date4Q(date4Q>date1(ii)-hours(2) & date4Q<date1(ii)+hours(2));
    if ~isempty(date4Q_tmp)
        [~, minIndex] = min(abs(date4Q-date1(ii)));
        Table.CAM4QUALI{ii} = CAM4QUALI_images(minIndex).name;
    else
        Table.CAM4QUALI{ii} = '.'; % fill with '.' when no image is available
    end
    date5_tmp = date5(date5>date1(ii)-hours(2) & date5<date1(ii)+hours(2));
    if ~isempty(date5_tmp)
        [~, minIndex] = min(abs(date5-date1(ii)));
        Table.CAM5{ii} = CAM5_images(minIndex).name;
    else
        Table.CAM5{ii} = '.'; % fill with '.' when no image is available
    end
end


% export table as csv
writetable(Table,[results_dir,'MasterTable_Period2.csv']);

% export each individual column as csv
for ii = 1:numel(Table.Properties.VariableNames)
    % Get the name of the current variable
    currentVariableName = Table.Properties.VariableNames{ii};
    
    % Extract the current column from the table
    currentColumn = Table.(currentVariableName);
    
    % Export the current column to a CSV file
    writetable(table(currentColumn), [results_dir,currentVariableName,'_selection_Period2.csv']);
end

%% write Image batch file for each row of the table

% read reference excel file
opts = delimitedTextImportOptions("NumVariables", 13);
opts.DataLines = [2, Inf];
opts.Delimiter = ";";
opts.VariableNames = ["Label", "x", "y", "z", "xAcc", "yAcc", "zAcc", "yaw", "pitch", "roll", "yawAcc", "pitchAcc", "rollAcc"];
opts.VariableTypes = ["string", "double", "double", "double", "double", "double", "double", "double", "double", "double", "double", "double", "double"];
opts.ExtraColumnsRule = "ignore";
opts.EmptyLineRule = "read";
opts = setvaropts(opts, "Label", "WhitespaceRule", "preserve");
opts = setvaropts(opts, "Label", "EmptyFieldRule", "auto");
Imbatch_ref = readtable("Z:\gl_kneibm\Projects\PI\2024_CAIRN-GLOBAL\TL_photogrammetry_Argentiere\data\TLCAM\CAM_selection\IMG_batch_1.csv", opts);
clear opts

for ii = 1:size(Table,1)
    Imbatch = Imbatch_ref;
    Imbatch.Label{1} = Table.CAM1{ii};
    if ~strcmp(Table.CAM2B{ii},'.')
        Imbatch.Label{2} = Table.CAM2B{ii};
    else
        Imbatch.Label{2} = '';
    end
    if ~strcmp(Table.CAM2N{ii},'.')
        Imbatch.Label{3} = Table.CAM2N{ii};
    else
        Imbatch.Label{3} = '';
    end
    if ~strcmp(Table.CAM3{ii},'.')
        Imbatch.Label{4} = Table.CAM3{ii};
    else
        Imbatch.Label{4} = '';
    end
    if ~strcmp(Table.CAM4B{ii},'.')
        Imbatch.Label{5} = Table.CAM4B{ii};
    else
        Imbatch.Label{5} = '';
    end
    if ~strcmp(Table.CAM4N{ii},'.')
        Imbatch.Label{6} = Table.CAM4N{ii};
    else
        Imbatch.Label{6} = '';
    end
    if ~strcmp(Table.CAM4QUALI{ii},'.')
        Imbatch.Label{7} = Table.CAM4QUALI{ii};
    else
        Imbatch.Label{7} = '';
    end
    if ~strcmp(Table.CAM5{ii},'.')
        Imbatch.Label{8} = Table.CAM5{ii};
    else
        Imbatch.Label{8} = '';
    end

    % remove the rows with empty values
    Imbatch(strcmp(Imbatch{:, 1},''),:) = [];

    % export as csv
    writetable(Imbatch,[results_dir,'Imbatch_Period2_',num2str(ii),'.csv']);
end




















